var app = app || {};

(function() {
    'use strict';

    app.ResultCollection = Backbone.Collection.extend({
        // Reference to this collection's model.
        model: app.Result,
        url: '/insight/api/v1.0/results',
        comparator: function(item) {
//            return item.get('instance_name');
            // HACK: "negate" strings to sort in reverse order
            // See: https://stackoverflow.com/questions/5013819/reverse-sort-order-with-backbone-js
            var str = item.get('created');
            str = str + item.get('instance_name');
            str = str.toLowerCase();
            str = str.split("");
            str = _.map(str, function(letter) { 
                return String.fromCharCode(-(letter.charCodeAt(0)));
            });
            return str;
        }
    });
})();
