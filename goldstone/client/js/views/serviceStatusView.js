/**
 * Copyright 2014 Solinea, Inc.
 *
 * Licensed under the Solinea Software License Agreement (goldstone),
 * Version 1.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *     http://www.solinea.com/goldstone/LICENSE.pdf
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Author: John Stanford
 */

 var ServiceStatusView = Backbone.View.extend({

    defaults: {},

    initialize: function(options) {
        this.options = options || {};
        this.defaults = _.clone(this.defaults);
        this.defaults.url = this.collection.url;
        this.defaults.location = options.location;
        this.defaults.width = options.width;

        this.collection.on('sync', this.update, this);
    },

    update: function() {
        var payload = this.collection.toJSON();

        var classSelector = function(item){
            if(item[0]){
                return 'alert alert-success';
            }
            return 'alert alert-danger';
        };

        _.each(payload, function(item, i) {
            $(this.defaults.location).append( '<div class="col-xs-2 ' + classSelector(_.values(payload[i])) + '">'  + _.keys(payload[i]) + '</div>');
        }, this);
        $(this.defaults.location).append('&nbsp;');
    }


});