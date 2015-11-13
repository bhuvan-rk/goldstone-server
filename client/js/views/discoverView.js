/**
 * Copyright 2015 Solinea, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

var DiscoverView = GoldstoneBasePageView.extend({

    triggerChange: function(change) {
        if (change === 'lookbackSelectorChanged') {
            this.eventTimelineChartView.trigger('lookbackSelectorChanged');
            this.nodeAvailChartView.trigger('lookbackSelectorChanged');
        }

        if (change === 'lookbackIntervalReached') {
            this.eventTimelineChartView.trigger('lookbackIntervalReached');
            this.nodeAvailChartView.trigger('lookbackIntervalReached');
        }
    },

    renderCharts: function() {

        //---------------------------
        // instantiate event timeline chart

        // fetch url is set in eventTimelineCollection
        this.eventTimelineChart = new EventTimelineCollection({});

        this.eventTimelineChartView = new EventTimelineView({
            collection: this.eventTimelineChart,
            el: '#goldstone-discover-r1-c1',
            chartTitle: goldstone.translate('Event Timeline'),
            width: $('#goldstone-discover-r1-c1').width()
        });

        //---------------------------
        // instantiate Node Availability chart

        this.nodeAvailChart = new NodeAvailCollection({});

        this.nodeAvailChartView = new NodeAvailView({
            chartTitle: goldstone.translate('Node Availability'),
            collection: this.nodeAvailChart,
            el: '#goldstone-discover-r1-c2',
            h: {
                "main": 150,
                "swim": 50
            },
            width: $('#goldstone-discover-r1-c2').width()
        });


        //---------------------------
        // instantiate Cloud Topology chart
        // Style of chart depends on user pref selected in settings page

        var topoTreePref = JSON.parse(localStorage.getItem('userPrefs'));

        this.discoverTree = new ZoomablePartitionCollection({});

        if (topoTreePref && topoTreePref.topoTreeStyle &&
            topoTreePref.topoTreeStyle === 'zoom') {

            // if user prefs designate 'zoom'able style
            this.zoomableTreeView = new ZoomablePartitionView({
                blueSpinnerGif: blueSpinnerGif,
                chartHeader: ['#goldstone-discover-r2-c1', goldstone.translate('Cloud Topology'),
                    'discoverZoomTopology'
                ],
                collection: this.discoverTree,
                el: '#goldstone-discover-r2-c1',
                h: 600,
                leafDataUrls: this.leafDataUrls,
                multiRsrcViewEl: '#goldstone-discover-r2-c2',
                width: $('#goldstone-discover-r2-c1').width()
            });

        } else {

            // if user prefs designate collapsable style
            var topologyTreeView = new TopologyTreeView({
                blueSpinnerGif: blueSpinnerGif,
                collection: this.discoverTree,
                chartHeader: ['#goldstone-discover-r2-c1', goldstone.translate('Cloud Topology'),
                    'discoverCloudTopology'
                ],
                el: '#goldstone-discover-r2-c1',
                h: 600,
                leafDataUrls: this.leafDataUrls,
                multiRsrcViewEl: '#goldstone-discover-r2-c2',
                width: $('#goldstone-discover-r2-c1').width(),
            });
        }


        //-----------------------------
        // instantiate new cloud topology chart

        this.discoverTreeNew = new ZoomablePartitionCollectionNew({});

        this.topologyTreeViewNew = new TopologyTreeViewNew({
                blueSpinnerGif: blueSpinnerGif,
                collection: this.discoverTreeNew,
                chartHeader: ['#goldstone-discover-r3-c1', goldstone.translate('Cloud Topology New'),
                    'discoverCloudTopology'
                ],
                el: '#goldstone-discover-r3-c1',
                h: 800,
                leafDataUrls: this.leafDataUrls,
                multiRsrcViewEl: '#goldstone-discover-r3-c2',
                width: $('#goldstone-discover-r3-c2').width(),
            });

    },

    // defined on the object to be used as common to both topo tree views above
    leafDataUrls: {
        "services-leaf": "/services",
        "endpoints-leaf": "/endpoints",
        "roles-leaf": "/roles",
        "users-leaf": "/users",
        "tenants-leaf": "/tenants",
        "agents-leaf": "/agents",
        "aggregates-leaf": "/aggregates",
        "availability-zones-leaf": "/availability_zones",
        "cloudpipes-leaf": "/cloudpipes",
        "flavors-leaf": "/flavors",
        "floating-ip-pools-leaf": "/floating_ip_pools",
        "hosts-leaf": "/hosts",
        "hypervisors-leaf": "/hypervisors",
        "networks-leaf": "/networks",
        "secgroups-leaf": "/security_groups",
        "servers-leaf": "/servers",
        "images-leaf": "/images",
        "volumes-leaf": "/volumes",
        "backups-leaf": "/backups",
        "snapshots-leaf": "/snapshots",
        "transfers-leaf": "/transfers",
        "volume-types-leaf": "/volume_types"
    },

    template: _.template('' +
        '<div id="goldstone-discover-r1" class="row">' +
        '<div id="goldstone-discover-r1-c1" class="col-md-6"></div>' +
        '<div id="goldstone-discover-r1-c2" class="col-md-6"></div>' +
        '</div>' +

        '<div id="goldstone-discover-r2" class="row">' +
        '<div id="goldstone-discover-r2-c1" class="col-md-6"></div>' +
        '<div id="goldstone-discover-r2-c2" class="col-md-6"></div>' +
        '</div>' +

        '<div class="row"></div>' +
        '<div class="row"></div>' +
        '<div class="row"></div>' +

        '<div id="goldstone-discover-r3" class="row">' +
        '<div id="goldstone-discover-r3-c1" class="col-md-6"></div>' +
        '<div id="goldstone-discover-r3-c2" class="col-md-6"></div>' +
        '</div>' +

        '<div class="row"><br><br></div>' +
        '<div class="row"><br><br></div>' +
        '<div class="row"><br><br></div>' +
        '<div class="row"><br><br></div>' +
        '<div class="row"><br><br></div>'

    )

});
