/**
 * Copyright 2014 - 2015 Solinea, Inc.
 *
 * Licensed under the Solinea Software License Agreement (goldstone),
 * Version 1.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *     http://www.solinea.com/goldstone/LICENSE.pdf
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
openstack syslog severity levels:
0       EMERGENCY: system is unusable
1       ALERT: action must be taken immediately
2       CRITICAL: critical conditions
3       ERROR: error conditions
4       WARNING: warning conditions
5       NOTICE: normal but significant condition
6       INFO: informational messages
7       DEBUG: debug-level messages
/*

/*
View is linked to collection when instantiated

Instantiated on discoverView as:

var nodeAvailChart = new NodeAvailCollection({});

var nodeAvailChartView = new NodeAvailView({
    collection: nodeAvailChart,
    h: {
        "main": 150,
        "swim": 50
        // "main": 450,
        // "swim": 50
    },
    el: '#goldstone-discover-r1-c2',
    chartTitle: 'Node Availability',
    width: $('#goldstone-discover-r2-c2').width()
});
*/


var NodeAvailView = GoldstoneBaseView.extend({

    defaults: {
        margin: {
            top: 18,
            bottom: 25,
            right: 40,
            left: 60
        },

        filter: {
            // none must be set to false in order to not display
            // nodes that have zero associated events.
            none: false,
            debug: true,
            info: true,
            notice: true,
            warning: true,
            error: true,
            critical: true,
            alert: true,
            emergency: true,
            actualZero: true
        }
    },

    initialize: function(options) {
        NodeAvailView.__super__.initialize.apply(this, arguments);
        this.setInfoButtonPopover();
        this.scheduleFetch();
    },

    processOptions: function() {
        this.el = this.options.el;
        this.defaults.chartTitle = this.options.chartTitle;
        this.defaults.width = this.options.width;
        this.defaults.height = this.options.h;
        this.defaults.r = d3.scale.sqrt();
        this.defaults.colorArray = new GoldstoneColors().get('colorSets');

    },

    processListeners: function() {
        this.collection.on('sync', this.update, this);
        this.collection.on('error', this.dataErrorMessage, this);
    },

    showSpinner: function() {
        var ns = this.defaults;
        var self = this;

        ns.spinnerDisplay = 'inline';

        var appendSpinnerLocation = this.el;
        $('<img id="spinner" src="' + blueSpinnerGif + '">').load(function() {
            $(this).appendTo(appendSpinnerLocation).css({
                'position': 'relative',
                'margin-left': (ns.width / 2),
                'margin-top': -(ns.height.main * 0.7),
                'display': ns.spinnerDisplay
            });
        });
    },

    standardInit: function() {
        var ns = this.defaults;
        var self = this;

        // maps between input label domain and output color range for circles
        ns.loglevel = d3.scale.ordinal()
            .domain(["emergency", "alert", "critical", "error", "warning", "notice", "info", "debug", "actualZero"])
        // concats darkgrey as a color for nodes
        // reported at 'actualZero'
        .range(ns.colorArray.distinct[8].concat(['#A9A9A9']));

        // for 'ping only' axis
        ns.pingAxis = d3.svg.axis()
            .orient("top")
            .ticks(5)
            .tickFormat(d3.time.format("%H:%M:%S"));

        // for 'disabled' axis
        ns.unadminAxis = d3.svg.axis()
            .orient("bottom")
            .ticks(5)
            .tickFormat(d3.time.format("%H:%M:%S"));

        ns.xScale = d3.time.scale()
            .range([ns.margin.left, ns.mw - ns.margin.right])
        // rounding
        .nice()
        // values above or below domain will be constrained to range
        .clamp(true);

        ns.yAxis = d3.svg.axis()
            .ticks(5)
            .orient("left");
        ns.swimAxis = d3.svg.axis().orient("left");
        ns.ySwimLane = d3.scale.ordinal()
            .domain(["unadmin"].concat(ns.loglevel
                .domain()
                .concat(["padding1", "padding2", "ping"])))
            .rangeRoundBands([ns.height.main, 0], 0.1);

        ns.yLogs = d3.scale.linear()
            .range([
                ns.ySwimLane("unadmin") - ns.ySwimLane.rangeBand(),
                ns.ySwimLane("ping") + ns.ySwimLane.rangeBand()
            ]);


        /*
         * The graph and axes
         */

        ns.svg = d3.select(this.el).select(".panel-body").append("svg")
            .attr("width", ns.width)
            .attr("height", ns.height.main + (ns.height.swim * 2) + ns.margin.top + ns.margin.bottom)
            .append("g")
            .attr("transform", "translate(" + ns.margin.left + "," + ns.margin.top + ")");

        ns.graph = ns.svg.append("g").attr("id", "graph");

        // Visual swim lanes
        ns.swimlanes = {
            ping: {
                label: "Ping Only",
                offset: -(ns.ySwimLane.rangeBand() / 2)
            },
            unadmin: {
                label: "Disabled",
                offset: ns.ySwimLane.rangeBand() / 2
            }
        };

        ns.graph.selectAll(".swimlane")
            .data(d3.keys(ns.swimlanes), function(d) {
                return d;
            })
            .enter().append("g")
            .attr("class", "swimlane")
            .attr("id", function(d) {
                return d;
            })
            .attr("transform", function(d) {
                return "translate(0," + ns.ySwimLane(d) + ")";
            });

        ns.graph.append("g")
            .attr("class", "xping axis")
            .attr("transform", "translate(0," + (ns.ySwimLane.rangeBand()) + ")");

        ns.graph.append("g")
            .attr("class", "xunadmin axis")
            .attr("transform", "translate(0," + (ns.height.main - ns.ySwimLane.rangeBand()) + ")");

        ns.graph.append("g")
            .attr("class", "y axis invisible-axis")
            .attr("transform", "translate(" + ns.mw + ",0)");

        // nudges visible y-axis to the right
        ns.graph.append("g")
            .attr("class", "swim axis invisible-axis")
            .attr("transform", "translate(20,0)");

        ns.tooltip = d3.tip()
            .attr('class', 'd3-tip')
            .direction(function(e) {
                if (e.update_method === 'PING') {
                    return 's';
                }
                if (this.getBBox().y < 130) {
                    return 's';
                } else {
                    return 'n';
                }
            })
            .offset(function() {
                var leftOffset;
                // [top-offset, left-offset]
                var toolTipWidth = 292;
                var halfToolHeight = 65;
                if (this.getBBox().x < toolTipWidth) {
                    leftOffset = toolTipWidth - this.getBBox().x;
                } else if (this.getBBox().x > ns.width - toolTipWidth) {
                    leftOffset = -(toolTipWidth - (ns.width - this.getBBox().x));
                } else {
                    leftOffset = 0;
                }
                return [0, leftOffset];
            })
            .html(function(d) {
                return d.name + "<br/>" +
                    // "(" + d.id + ")" + "<br/>" +
                    "Emergency: " + d.emergency_count + "<br>" +
                    "Alert: " + d.alert_count + "<br>" +
                    "Critical: " + d.critical_count + "<br>" +
                    "Error: " + d.error_count + "<br>" +
                    "Warning: " + d.warning_count + "<br>" +
                    "Notice: " + d.notice_count + "<br>" +
                    "Info: " + d.info_count + "<br>" +
                    "Debug: " + d.debug_count + "<br>";
            });

        ns.graph.call(ns.tooltip);

        // Label the swim lane ticks
        ns.swimAxis
            .tickFormat(function(d) {
                // Visual swim lanes
                var swimlanes = {
                    ping: "Ping Only",
                    unadmin: "Disabled",
                };
                var middle = ns.ySwimLane.domain()[Math.floor(ns.ySwimLane.domain().length / 2)];
                swimlanes[middle] = "Logs";
                if (swimlanes[d]) {
                    return swimlanes[d];
                } else {
                    return "";
                }
            });

        // Draw the axis on the screen
        d3.select(this.el).select(".swim.axis")
            .call(ns.swimAxis.scale(ns.ySwimLane));

        // Transform the swim lane ticks into place
        // increases size of labels via font-size
        d3.select(this.el).select(".swim.axis").selectAll("text")
            .style('font-size', '15px')
            .style('font-weight', 'bold');
    },

    scheduleFetch: function() {
        var ns = this.defaults;
        var self = this;

        var timeoutDelay = 30000;

        ns.scheduleTimeout = setInterval(function() {
            self.showSpinner();
            self.collection.fetchWithReset();
        }, timeoutDelay);
    },

    sums: function(datum) {
        var ns = this.defaults;
        // Return the sums for the filters that are on
        return d3.sum(ns.loglevel.domain().map(function(k) {

            if (ns.filter[k]) {
                return datum[k + "_count"];
            } else {
                return 0;
            }

        }));
    },

    collectionPrep: function(data) {
        var finalData = [];


        // data.levels will equal all hosts
        // make an object to keep track of whether each one has been
        var setOfHosts = {}; // ['rsrc-01', 'ctrl-01', ....]

        // prime setOfHosts object. keyed to data.hosts
        // and value all initially set to null
        _.each(data.hosts, function(item) {
            setOfHosts[item] = null;
        }); // {'rsrc-01: null, 'ctrl-01': null, ...}

        // function to return if there are any keys that have
        // a value of null in the passed in object
        // (which will be used with setOfHosts)
        var checkIfAnyNull = function(obj) {
            return _.any(obj, function(item) {
                return item === null;
            });
        };

        // sets up an iteration that will break as soon as every
        // host value is no longer set to null, or else gets
        // through the entire data set
        _.every(data.data, function(item) {

            // iterate through the timestamp
            _.each(item, function(hostsInTimestamp, timestamp) {

                // iterate through the host
                _.each(hostsInTimestamp, function(hostObject) {

                    var hostName = _.keys(hostObject)[0];
                    if (setOfHosts[hostName] === null) {

                        // don't run through this host again
                        setOfHosts[hostName] = true;
                        hostResultObject = {};

                        // add in params that are expected by current viz:
                        hostResultObject.id = hostName;
                        hostResultObject.name = hostName;
                        hostResultObject.updated = +timestamp;
                        hostResultObject.managed = true;
                        hostResultObject.update_method = "LOGS";

                        // iterate through host and record the values
                        _.each(hostObject, function(levels) {
                            _.each(levels, function(oneLevel) {
                                hostResultObject[_.keys(oneLevel) + '_count'] = _.values(oneLevel)[0];
                            });
                        });

                        finalData.push(hostResultObject);
                    }
                });
            });

            // if there are any remaining hosts that are set to null
            // then this retrun value will be true and the iteration
            // will continue. but if this returns false, it stops
            return checkIfAnyNull(setOfHosts);
        });


        // found in the data.data array, and record the levels
        // and timestamp for that occurance.
        // once each host has been found, quit the iteration and
        // return the record as final data;

        console.log('finaldata', finalData);
        return finalData;
    },

    update: function() {
        var ns = this.defaults;
        var self = this;

        this.hideSpinner();

        // includes timestamps, levels, hosts, data
        var allthelogs = this.collection.toJSON()[0];

        var xStart = +new Date();

        var xEnd = xStart - (1000 * 60 * 15);

        ns.xScale = ns.xScale.domain([xStart, xEnd]);

        // If we didn't receive any valid files, append "No Data Returned"
        if (this.checkReturnedDataSet(allthelogs.data) === false) {
            return;
        }

        // populate the modal based on the event types.
        // clear out the modal and reapply based on the unique events
        if ($(this.el).find('#populateEventFilters').length) {
            $(this.el).find('#populateEventFilters').empty();
        }

        _.each(_.keys(ns.filter), function(item) {

            // don't put type 'none' or 'actualZero'
            // in the modal checkbox options
            if (item === 'none' || item === 'actualZero') {
                return null;
            }

            var addCheckIfActive = function(item) {
                if (ns.filter[item]) {
                    return 'checked';
                } else {
                    return '';
                }
            };

            var checkMark = addCheckIfActive(item);

            $(self.el).find('#populateEventFilters').
            append(

                '<div class="row">' +
                '<div class="col-lg-12">' +
                '<div class="input-group">' +
                '<span class="input-group-addon"' +
                'style="opacity: 0.8; background-color:' + ns.loglevel([item]) + ';">' +
                '<input id="' + item + '" type="checkbox" ' + checkMark + '>' +
                '</span>' +
                '<span type="text" class="form-control">' + item + '</span>' +
                '</div>' +
                '</div>' +
                '</div>'
            );
        });

        $(this.el).find('#populateEventFilters :checkbox').on('click', function() {
            var checkboxId = this.id;
            ns.filter[checkboxId] = !ns.filter[checkboxId];
            self.redraw();

        });


        /*
         * Shape the dataset
         *   - Convert datetimes to integer
         *   - Sort by last seen (from most to least recent)
         */

        ns.dataset = this.collectionPrep(allthelogs)
            .map(function(d) {
                d.created = moment(d.created);
                d.updated = moment(d.updated);

                /*
                 * Figure out which bucket (logs, ping, or disabled)
                 * each node belongs to.
                 */

                if (d.managed === "false") {
                    d.swimlane = "unadmin";
                } else {
                    d.swimlane = d.update_method.toLowerCase();
                }
                return d;
            });


        /*
         * Axes
         *   - calculate the new domain.
         *   - adjust each axis to its new scale.
         */

        ns.pingAxis.scale(ns.xScale);
        ns.unadminAxis.scale(ns.xScale);

        ns.svg.select(".xping.axis")
            .call(ns.pingAxis);

        ns.svg.select(".xunadmin.axis")
            .call(ns.unadminAxis);

        ns.yAxis.scale(ns.yLogs);

        ns.svg.select(".y.axis")
            .transition()
            .duration(500)
            .call(ns.yAxis);


        // binds circles to dataset
        var circle = ns.graph.selectAll("circle")
            .data(ns.dataset, function(d) {
                // if changing this, also must
                // change idAttribute in backbone model

                /*
TODO: probably change this to d.timestamp
*/
                return d.id;
            });

        // 'enters' circles at far right of screen.
        // styling and location will happen in this.redraw().
        circle.enter()
            .append("circle")
            .attr("cx", function(d) {
                return ns.xScale.range()[1];
            })
            .attr("cy", function(d) {
                return ns.yLogs(self.sums(d));
            })
            .on("mouseover", ns.tooltip.show)
            .on("mouseout", ns.tooltip.hide)
            .on("click", function(d) {
                window.location.href = '/report/node/' + d.name;
            });

        this.redraw();

        circle.exit().remove();

        return true;
    },

    redraw: function() {
        var ns = this.defaults;
        var self = this;

        /*
         * Figure out the higest non-filtered level.
         * That will determine its color.
         */

        _.each(ns.dataset, function(nodeObject) {

            // nonzero_levels returns an array of the node's
            // alert severities that are not filtered out

            var nonzero_levels = ns.loglevel.domain()
                .map(function(level) {
                    return [level, nodeObject[level + "_count"]];
                })
                .filter(function(level) {

                    // only consider 'active' filter buttons
                    return ns.filter[level[0]] && (level[1] > 0);
                });

            // the .level paramater will determine visibility
            // and styling of the sphere

            // if the array is empty:
            if (nonzero_levels[0] === undefined) {
                nodeObject.level = "actualZero";
            } else {

                // otherwise set it to the
                // highest alert severity
                nodeObject.level = nonzero_levels[nonzero_levels.length - 1][0];
            }

        });

        ns.yLogs.domain([
            0,
            d3.max(ns.dataset.map(function(d) {
                return self.sums(d);
            }))
        ]);

        d3.select(this.el).select(".swim.axis")
            .transition()
            .duration(500);

        d3.select(this.el).select(".y.axis")
            .transition()
            .duration(500)
            .call(ns.yAxis.scale(ns.yLogs));

        ns.graph.selectAll("circle")
            .transition().duration(500)
        // this determines the color of the circle
        .attr("class", function(d) {
            if (d.swimlane === "unadmin") {
                return d.swimlane;
            } else {
                return "individualNode";
            }
        })
            .attr("fill", function(d) {
                return ns.loglevel(d.level);
            })
            .attr("cx", function(d) {
                return ns.xScale(d.updated);
            })
            .attr("cy", function(d, i) {

                // add multiplier to give space between
                // multiple items reporting the same numbers
                if (d.level === 'actualZero') {
                    return (ns.yLogs(self.sums(d)) - (i * 2));
                } else {

                    // notice the [] at the end which is calling
                    // the key that matches d.swimlane

                    return {

                        // add multiplier to give space between
                        // multiple items reporting the same numbers
                        logs: ns.yLogs(self.sums(d) - (i * 2)),

                        ping: ns.ySwimLane(d.swimlane) - 15,
                        unadmin: ns.ySwimLane(d.swimlane) + ns.ySwimLane.rangeBand() + 15
                    }[d.swimlane];


                }



            })
            .attr("r", function(d) {

                // radii at fixed size for now.
                if (d.swimlane === "logs") {
                    return ns.r(64);
                } else {
                    return ns.r(20);
                }

            })
            .style("opacity", function(d) {

                if (d.swimlane === "unadmin") {
                    return 0.8;
                }
                if (ns.filter[d.level]) {
                    return 0.8;
                } else {
                    return 0;
                }

            })
            .style("visibility", function(d) {

                // use visibility "hidden" to
                // completely remove from dom to prevent
                // tool tip hovering from still working
                if (!ns.filter[d.level]) {
                    return "hidden";
                } else {
                    return "visible";
                }
            });

    },

    render: function() {
        this.$el.html(this.template());
        // this.$el.find('#modal-container-' + this.el.slice(1)).append(this.modal1());
        this.$el.find('#modal-container-' + this.el.slice(1)).append(this.modal2());
        return this;
    },

    setInfoButtonPopover: function() {

        var infoButtonText = new InfoButtonText().get('infoText');

        // attach click listeners to chart heading info button
        $('#goldstone-node-info').popover({
            trigger: 'manual',
            content: '<div class="infoButton">' +
                infoButtonText.nodeAvailability +
                '</div>',
            placement: 'bottom',
            html: 'true'
        })
            .on("click", function(d) {
                var targ = "#" + d.target.id;
                $(targ).popover('toggle');
            }).on("mouseout", function(d) {
                var targ = "#" + d.target.id;
                $(targ).popover('hide');
            });
    },

    template: _.template(
        '<div id = "goldstone-node-panel" class="panel panel-primary">' +
        '<div class="panel-heading">' +
        '<h3 class="panel-title"><i class="fa fa-tasks"></i> ' +
        '<%= this.defaults.chartTitle %>' +

        // cog icon
        // '<i class="fa fa-cog pull-right" data-toggle="modal"' +
        // 'data-target="#modal-settings-<%= this.el.slice(1) %>' +
        // '"></i>' +

        // filter icon
        '<i class="fa fa-filter pull-right" data-toggle="modal"' +
        'data-target="#modal-filter-<%= this.el.slice(1) %>' + '" style="margin-right: 15px;"></i>' +

        // info-circle icon
        '<i class="fa fa-info-circle panel-info pull-right "  id="goldstone-node-info"' +
        'style="margin-right: 15px;"></i>' +
        '</h3></div>' +
        '<div class="alert alert-danger popup-message" hidden="true"></div>' +
        '<div class="panel-body" style="height:169px">' +
        '<div id="event-filterer" class="btn-group pull-right" data-toggle="buttons" align="center">' +
        '</div>' +
        '</div>' +
        '<div id="goldstone-node-chart">' +
        '<div class="clearfix"></div>' +
        '</div>' +
        '</div>' +
        '</div>' +

        '<div id="modal-container-<%= this.el.slice(1) %>' +
        '"></div>'

    ),

    modal1: _.template(
        // event settings modal
        '<div class="modal fade" id="modal-settings-<%= this.el.slice(1) %>' +
        '" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">' +
        '<div class="modal-dialog">' +
        '<div class="modal-content">' +

        // header
        '<div class="modal-header">' +
        '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
        '<h4 class="modal-title" id="myModalLabel">Chart Settings</h4>' +
        '</div>' +

        // body
        '<div class="modal-body">' +
        '<form class="form-horizontal" role="form">' +
        '<div class="form-group">' +
        '<label for="nodeAutoRefresh" class="col-sm-3 control-label">Refresh: </label>' +
        '<div class="col-sm-9">' +
        '<div class="input-group">' +
        '<span class="input-group-addon">' +
        '<input type="checkbox" class="nodeAutoRefresh" checked>' +
        '</span>' +
        '<select class="form-control" id="nodeAutoRefreshInterval">' +
        '<option value="5">5 seconds</option>' +
        '<option value="15">15 seconds</option>' +
        '<option value="30" selected>30 seconds</option>' +
        '<option value="60">1 minute</option>' +
        '<option value="300">5 minutes</option>' +
        '</select>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '</form>' +
        '</div>' +

        // footer
        '<div class="modal-footer">' +
        '<div class="form-group">' +
        '<button type="button" id="eventSettingsUpdateButton-<%= this.el.slice(1) %>' +
        '" class="btn btn-primary" data-dismiss="modal">Update</button>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '</div>'
    ),

    modal2: _.template(
        // event filter modal
        '<div class="modal fade" id="modal-filter-<%= this.el.slice(1) %>' +
        '" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">' +
        '<div class="modal-dialog">' +
        '<div class="modal-content">' +

        // header
        '<div class="modal-header">' +
        '<button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>' +
        '<h4 class="modal-title" id="myModalLabel">Log Severity Filters</h4>' +
        '</div>' +

        // body
        '<div class="modal-body">' +
        '<h5>Uncheck log-type to hide from display</h5><br>' +
        '<div id="populateEventFilters"></div>' +
        '</div>' +

        // footer
        '<div class="modal-footer">' +
        '<button type="button" id="eventFilterUpdateButton-<%= this.el.slice(1) %>' +
        '" class="btn btn-primary" data-dismiss="modal">Exit</button>' +
        '</div>' +

        '</div>' +
        '</div>' +
        '</div>'
    )
});
