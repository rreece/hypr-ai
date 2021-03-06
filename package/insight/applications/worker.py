import argparse
import os
import json
import pickle
from urllib.parse import urlparse
from insight.storage import DBJobInstance, DBInsightModels, DBInstanceLog, S3DB
from insight.builder import Convert
from simple_settings import LazySettings
from keras.callbacks import RemoteMonitor, ModelCheckpoint, EarlyStopping
from keras.utils import to_categorical
import keras.backend as K

settings = LazySettings('insight.applications.settings')


'''
    This is the main entry point of docker container
'''


def start_pipeline():
    # startup parameters parsering
    cmdParser = argparse.ArgumentParser(description='')
    cmdParser.add_argument('-i', '--instance', dest='instance_name', help="Job instance name")
    cmdParser.add_argument('-m', '--model', dest='model_name', help='Model defination')
    cmdParser.add_argument('-w', '--weights', dest='pretrained_model', help="pretrained model weights file of s3 bucket")
    cmdParser.add_argument('-d', '--dataset', dest='training_dataset', help="training dataset objetct of s3 bucket")
    cmdParser.add_argument('-s', '--service', dest='monitor_service', help="service that monitor training")
    args = cmdParser.parse_args()
    if args.instance_name is None or args.model_name is None or args.training_dataset is None or args.monitor_service is None:
        cmdParser.print_help()
        exit()

    remote_log = DBInstanceLog(args.instance_name)
    job_instance = DBJobInstance()
    instance = job_instance.get(args.instance_name)
    if instance is None:
        print("Instance doesn't exist, abort!")

    weights_file = args.pretrained_model

    print(args.monitor_service)
    if not args.monitor_service:
        print('monitor service error')
        return

    parsed = urlparse(args.monitor_service)
    monitor_host = parsed.scheme + "://" + parsed.netloc
    monitor_path = parsed.path + "/" + args.instance_name

    log = 'Job: {}, model: {}, dataset: {}, pre-train: {}, monitor: {}'.format(
        args.instance_name, args.model_name, args.training_dataset, weights_file, args.monitor_service
    )
    print(log)
    remote_log.append('info', log)

    # settings = json.loads(os.environ['APP_SETTINGS'])
    # fetch JSON model from central DB
    db_model = DBInsightModels()
    original_json = db_model.get(args.model_name)

    # download weights file if required
    if args.pretrained_model != "NONE":
        s3_results = S3DB(bucket_name=settings.S3_BUCKET['RESULTS'])
        weights_file = './{}.weights'.format(args.model_name)
        remote_log.append('info', 'downloading pretrained weights: {}'.format(args.pretrained_model))
        s3_results.download(args.pretrained_model, weights_file)

    remote_log.append('info', 'compiling keras model: {}'.format(args.model_name))

    conv = Convert()
    parent_json = conv.check_inheritance(original_json)
    if parent_json:
        remote_log.append('info', 'retrieving parent model: {}'.format(parent_json))
        parent_json = db_model.get(parent_json)

    if weights_file != 'NONE':
        keras_model = conv.parser(original_json, parent_json, weights_file=weights_file)
    else:
        keras_model = conv.parser(original_json, parent_json)
    
    remote_log.append('info', keras_model.summary())

    # download dataset
    remote_log.append('info', 'downloading dataset: {}*'.format(args.training_dataset))
    s3_dataset = S3DB(bucket_name=settings.S3_BUCKET['DATASET'])

    s3_train_file = args.training_dataset + '-train.tar.gz'
    s3_test_file = args.training_dataset + '-test.tar.gz'

    train_file = os.path.basename(args.training_dataset + '-train')
    test_file = os.path.basename(args.training_dataset + '-test')
    
    s3_dataset.download(s3_train_file, './{}.tar.gz'.format(train_file))
    s3_dataset.download(s3_test_file, './{}.tar.gz'.format(test_file))

    train_p_file = 'train.p'
    test_p_file = 'test.p'

    # load dataset
    remote_log.append('info', 'loading dataset...')
    with open(train_p_file, 'rb') as f:
        train_frame = pickle.load(f)
    with open(test_p_file, 'rb') as f:
        test_frame = pickle.load(f)
    
    x_train, y_train = train_frame['data'], train_frame['labels']
    x_test, y_test = test_frame['data'], test_frame['labels']

    if K.image_data_format() == 'channels_last' and x_train.shape[1] <= 3:
        x_train = x_train.transpose(0, 2, 3, 1)
        x_test = x_test.transpose(0, 2, 3, 1)

    # training
    model_file = args.instance_name + '.hdf5'

    cbMonitor = RemoteMonitor(root=monitor_host, path=monitor_path, field='data', headers=None)
    cbEarlyStop = EarlyStopping(min_delta=0.001, patience=3)
    cbModelsCheckpoint = ModelCheckpoint(
        './' + model_file,
        monitor='val_loss',
        verbose=1,
        save_best_only=True,
        save_weights_only=True,
        mode='auto',
        period=1
    )

    remote_log.append('info', 'training...')
    history = keras_model.fit(
        x_train / 255.0, to_categorical(y_train),
        validation_data=(x_test / 255.0, to_categorical(y_test)),
        shuffle=True,
        batch_size=128,
        verbose=1,
        epochs=int(instance['epochs']),
        callbacks=[cbEarlyStop, cbMonitor, cbModelsCheckpoint]
    )

    # upload models
    remote_log.append('info', 'uploading trained model to s3')
    s3_models = S3DB(bucket_name=settings.S3_BUCKET['RESULTS'])
    s3_models.upload(model_file, model_file)

    
    job_instance.update_status(args.instance_name, from_='training', to_='completed')
    remote_log.append('info', 'done')


if __name__ == "__main__":
    start_pipeline()
