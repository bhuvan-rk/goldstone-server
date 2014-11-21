/*global sinon, todo, chai, describe, it, calledOnce*/
//integration tests - nodeAvailView.js

describe('nodeAvailView.js spec', function() {
    beforeEach(function() {
        $('body').html('<div class="testContainer"></div>' +
            '<div style="width:10%;" class="col-xl-1 pull-right">&nbsp;' +
            '</div>' +
            '<div class="col-xl-2 pull-right">' +
            '<form class="global-refresh-selector" role="form">' +
            '<div class="form-group">' +
            '<div class="col-xl-1">' +
            '<div class="input-group">' +
            '<select class="form-control" id="global-refresh-range">' +
            '<option value="15">refresh 15s</option>' +
            '<option value="30" selected>refresh 30s</option>' +
            '<option value="60">refresh 1m</option>' +
            '<option value="300">refresh 5m</option>' +
            '<option value="-1">refresh off</option>' +
            '</select>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</form>' +
            '</div>' +
            '<div class="col-xl-1 pull-right">' +
            '<form class="global-lookback-selector" role="form">' +
            '<div class="form-group">' +
            '<div class="col-xl-1">' +
            '<div class="input-group">' +
            '<select class="form-control" id="global-lookback-range">' +
            '<option value="15">lookback 15m</option>' +
            '<option value="60" selected>lookback 1h</option>' +
            '<option value="360">lookback 6h</option>' +
            '<option value="1440">lookback 1d</option>' +
            '</select>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</form>' +
            '</div>');

        // to answer GET requests
        this.server = sinon.fakeServer.create();
        this.server.respondWith("GET", "/*", [200, {
            "Content-Type": "application/json"
        }, '{absolutely: "nothing"}']);

        // confirm that dom is clear of view elements before each test:
        expect($('svg').length).to.equal(0);
        expect($('#spinner').length).to.equal(0);

        this.testCollection = new NodeAvailCollection({
            url: '/something/fancy',
        });
        this.testCollection.reset();
        this.testCollection.add([{
            "uuid": "46b24373-eedc-43d5-9543-19dea317d88f",
            "name": "compute-01",
            "created": "2014-10-27T19:26:17Z",
            "updated": "2014-10-28T18:32:18Z",
            "last_seen_method": "LOGS",
            "admin_disabled": false,
            "error_count": 10,
            "warning_count": 4,
            "info_count": 33,
            "audit_count": 551,
            "debug_count": 4,
            "polymorphic_ctype": 12
        }, {
            "uuid": "d0656d75-1c26-48c5-875b-9130dd8892f4",
            "name": "compute-02",
            "created": "2014-10-27T19:27:17Z",
            "updated": "2014-10-28T18:33:17Z",
            "last_seen_method": "LOGS",
            "admin_disabled": false,
            "error_count": 1,
            "warning_count": 2,
            "info_count": 3,
            "audit_count": 448,
            "debug_count": 5,
            "polymorphic_ctype": 12
        }, {
            "uuid": "46b24373-eedc-43d5-9543-19dea317d88f",
            "name": "controller-01",
            "created": "2014-10-27T19:29:17Z",
            "updated": "2014-10-28T18:38:18Z",
            "last_seen_method": "LOGS",
            "admin_disabled": false,
            "error_count": 10,
            "warning_count": 4,
            "info_count": 33,
            "audit_count": 551,
            "debug_count": 0,
            "polymorphic_ctype": 12
        }]);

        blueSpinnerGif = "goldstone/static/images/ajax-loader-solinea-blue.gif";

        this.testView = new NodeAvailView({
            collection: this.testCollection,
            h: {
                "main": 450,
                "swim": 50
            },
            el: '.testContainer',
            chartTitle: "Test Chart Title",
            width: 500
        });
    });
    afterEach(function() {
        $('body').html('');
        this.server.restore();
    });
    describe('collection is constructed', function() {
        it('should exist', function() {
            assert.isDefined(this.testCollection, 'this.testCollection has been defined');
            expect(this.testCollection.parse).to.be.a('function');
            expect(this.testCollection.length).to.equal(2);
            this.testCollection.add({
                test1: 'test1'
            });
            expect(this.testCollection.length).to.equal(3);
            this.testCollection.pop();
            expect(this.testCollection.length).to.equal(2);
            this.testCollection.setXhr();
        });
        it('should parse appropriate', function() {
            var testData = {
                a: "blah",
                b: "wah",
                results: [1, 2, 3]
            };
            var test1 = this.testCollection.parse(testData);
            expect(test1).to.deep.equal([1, 2, 3]);
            testData = {
                a: "blah",
                b: "wah",
                results: [1, 2, 3],
                next: null
            };
            var test2 = this.testCollection.parse(testData);
            expect(test2).to.deep.equal([1, 2, 3]);
            testData = {
                a: "blah",
                b: "wah",
                results: [1, 2, 3],
                next: 'fantastic/loggin/urls/forever'
            };
            var test3 = this.testCollection.parse(testData);
            expect(test3).to.deep.equal([1, 2, 3]);
        });
    });

    describe('view is constructed', function() {
        it('should exist', function() {
            assert.isDefined(this.testView, 'this.testView has been defined');
            expect(this.testView).to.be.an('object');
            expect(this.testView.el).to.equal('.testContainer');
        });
        it('view update appends svg and border elements', function() {
            expect(this.testView.update).to.be.a('function');
            expect($('svg').length).to.equal(1);
            expect($('g').find('.axis').text()).to.equal('DisabledLogsPing Only');
            expect($('.panel-title').text().trim()).to.equal('Test Chart Title');
            expect($('svg').text()).to.not.include('Response was empty');
        });
        it('can handle a null server payload and append appropriate response', function() {
            this.update_spy = sinon.spy(this.testView, "update");
            expect($('#noDataReturned').length).to.equal(0);
            expect($('#noDataReturned').text()).to.equal('');
            this.testCollection.reset();
            this.testView.update();
            expect($('.testContainer').find('#noDataReturned').length).to.equal(1);
            expect($('#noDataReturned').text()).to.equal('No Data Returned');
            // it doesn't RE-apply 'No Data Returned' if it's already there:
            this.testView.update();
            expect($('.testContainer').find('#noDataReturned').length).to.equal(1);
            expect($('#noDataReturned').text()).to.equal('No Data Returned');
            // it REMOVES 'No Data Returned' if data starts flowing again:
            this.testCollection.add({
                "uuid": "46b24373-eedc-43d5-9543-19dea317d88f",
                "name": "compute-01",
                "created": "2014-10-27T19:27:17Z",
                "updated": "2014-10-28T18:33:18Z",
                "last_seen_method": "LOGS",
                "admin_disabled": true,
                "error_count": 10,
                "warning_count": 4,
                "info_count": 33,
                "audit_count": 551,
                "debug_count": 0,
                "polymorphic_ctype": 12
            });
            this.testView.update();
            expect($('.testContainer').find('#noDataReturned').length).to.equal(0);
            expect($('#noDataReturned').text()).to.equal('');
            expect(this.update_spy.callCount).to.equal(3);
            this.update_spy.restore();
        });
        it('populates the event filters', function() {
            this.testView.update();
            expect($('#populateEventFilters').children().length).to.equal(5);
        });
        it('sums appropriately based on filter and count', function() {
            var testData = {
                "info_count": 42
            };
            var test1 = this.testView.sums(testData);
            expect(test1).to.equal(42);

            this.testView.defaults.filter.info_count = false;
            testData = {
                "info_count": 0
            };
            var test2 = this.testView.sums(testData);
            expect(test2).to.equal(0);

            this.testView.defaults.filter.info = false;
            testData = {
                "info_count": 42
            };
            var test3 = this.testView.sums(testData);
            expect(test3).to.equal(0);
        });
        it('redraws successfully', function() {
            expect(this.testView.redraw).is.a('function');

            this.testView.defaults.dataset = this.testCollection.toJSON();

            this.testView.redraw();
        });
        it('appends circles upon update', function() {
            expect($('svg').find('circle').length).to.equal(0);
            this.testView.update();
            expect($('svg').find('circle').length).to.equal(2);
        });
        it('registers changes on the global lookback/refresh selectors', function() {

            this.clearScheduledSpy = sinon.spy(this.testView, "clearScheduledFetch");
            this.updateSettingsSpy = sinon.spy(this.testView, "updateSettings");
            this.scheduleFetchSpy = sinon.spy(this.testView, "scheduleFetch");

            expect(this.clearScheduledSpy.callCount).to.equal(0);
            expect(this.updateSettingsSpy.callCount).to.equal(0);
            expect(this.scheduleFetchSpy.callCount).to.equal(0);

            $('.global-refresh-selector .form-control').trigger('change');
            expect(this.clearScheduledSpy.callCount).to.equal(2);
            expect(this.updateSettingsSpy.callCount).to.equal(1);
            expect(this.scheduleFetchSpy.callCount).to.equal(1);
            this.clearScheduledSpy.restore();
            this.updateSettingsSpy.restore();
            this.scheduleFetchSpy.restore();
        });
        it('scheduleFetch short-circuits if pause is true', function() {
            this.testView.defaults.scheduleTimeout = null;

            this.scheduleFetchSpy = sinon.spy(this.testView, "scheduleFetch");
            this.clearScheduledSpy = sinon.spy(this.testView, "clearScheduledFetch");

            expect(this.clearScheduledSpy.callCount).to.equal(0);
            expect(this.scheduleFetchSpy.callCount).to.equal(0);

            this.testView.defaults.delay = -1;

            this.testView.scheduleFetch();

            expect(this.clearScheduledSpy.callCount).to.equal(1);
            expect(this.scheduleFetchSpy.callCount).to.equal(1);
            expect(this.testView.defaults.scheduleTimeout).to.equal(null);

            this.testView.defaults.delay = 1;
            this.testView.scheduleFetch();

            expect(this.clearScheduledSpy.callCount).to.equal(2);
            expect(this.scheduleFetchSpy.callCount).to.equal(2);
            expect(this.testView.defaults.scheduleTimeout).to.not.equal(null);

            this.scheduleFetchSpy.restore();
            this.clearScheduledSpy.restore();
        });
        it('correctly identifies if refresh is selected', function() {
            var test1 = this.testView.isRefreshSelected();
            expect(test1).to.equal(true);
            $('.global-refresh-selector .form-control').val(-1);
            var test2 = this.testView.isRefreshSelected();
            expect(test2).to.equal(false);
        });
        // pending lookback functionality
        // it('correctly identifies the lookback range', function() {
        //     var test1 = this.testView.lookbackRange();
        //     expect(test1).to.equal(60);
        //     $('.global-lookback-selector .form-control').val(360);
        //     var test2 = this.testView.lookbackRange();
        //     expect(test2).to.equal(360);
        // });
        it('correctly identifies the refresh rate', function() {
            var test1 = this.testView.refreshInterval();
            expect(test1).to.equal(30);
            $('.global-refresh-selector .form-control').val(60);
            var test2 = this.testView.refreshInterval();
            expect(test2).to.equal(60);
        });
    });
});
