import argparse
import os
import json
from simple_settings import LazySettings

#import pickle
#from urllib.parse import urlparse
#from keras.callbacks import RemoteMonitor, ModelCheckpoint, EarlyStopping
#from keras.utils import to_categorical
#import keras.backend as K

from insight.storage import DBJobInstance, DBInsightModels, DBInstanceLog, S3DB
from insight.builder import Convert

settings = LazySettings('insight.applications.settings')

#______________________________________________________________________________
def options():
    cmdParser = argparse.ArgumentParser(description='')
    cmdParser.add_argument('-i', '--instance', dest='instance_name', help="Job instance name")
    cmdParser.add_argument('-m', '--model', dest='model_name', help='Model defination')
    cmdParser.add_argument('-w', '--weights', dest='pretrained_model', help="pretrained model weights file of s3 bucket")
    cmdParser.add_argument('-d', '--dataset', dest='training_dataset', help="training dataset objetct of s3 bucket")
    cmdParser.add_argument('-s', '--service', dest='monitor_service', help="service that monitor training")
    cmdParser.add_argument('-p', '--hparams', dest='hparams', help="hyperparameter dictionary", default=None)
    args = cmdParser.parse_args()
#    if args.instance_name is None or args.model_name is None or args.training_dataset is None or args.monitor_service is None:
#        cmdParser.print_help()
#        exit()
    return args


#______________________________________________________________________________
def main():
    args = options()

    remote_log = DBInstanceLog(args.instance_name)
    log = remote_log.fetch(True)
    print(log)


if __name__ == "__main__":
    main()
