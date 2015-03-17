/**
 * Copyright 2015 Solinea, Inc.
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

var SettingsPageView = Backbone.View.extend({

    initialize: function(options) {
        this.options = options || {};
        this.defaults = _.clone(this.defaults);
        this.el = options.el;
        this.render();
        this.getUserSettings();
        this.addHandlers();
    },

    addHandlers: function() {
        var self = this;

        // add listener to settings form submission button
        $('.settings-form').on('submit', function(e) {
            e.preventDefault();

            // trim inputs to prevent leading/trailing spaces
            self.trimInputField('[name="username"]');
            self.trimInputField('[name="first_name"]');
            self.trimInputField('[name="last_name"]');

            // ('[name="email"]') seems to have native .trim()
            // support based on the type="email"

            self.submitRequest('PUT', '/user', $(this).serialize(), 'Settings');
        });

        // add listener to password form submission button
        $('.password-reset-form').on('submit', function(e) {
            e.preventDefault();
            self.submitRequest('POST', '/accounts/password', $(this).serialize(), 'Password');

            // clear password form after submission, success or not
            $('.password-reset-form').find('[name="current_password"]').val('');
            $('.password-reset-form').find('[name="new_password"]').val('');
        });
    },

    getUserSettings: function() {
        $.get('/user')
            .done(function(result) {
                $('[name="username"]').val(result.username);
                $('[name="first_name"]').val(result.first_name);
                $('[name="last_name"]').val(result.last_name);
                $('[name="email"]').val(result.email);
            })
            .fail(function(fail) {
                goldstone.raiseInfo('Could not load user settings', true);
            });
    },

    // abstracted to work for both forms, and append the correct
    // message upon successful form submission
    submitRequest: function(type, url, data, message) {
        var self = this;

        // Upon clicking the submit button, the serialized
        // user input is sent via type (POST/PUT/etc).
        // If successful, invoke "done". If not, invoke "fail"

        $.ajax({
            type: type,
            url: url,
            data: data,
        }).done(function(success) {
            goldstone.raiseInfo(message + ' update successful', true);
        })
            .fail(function(fail) {
                try {
                    goldstone.raiseInfo(fail.responseJSON.non_field_errors[0], true);
                } catch (e) {
                    goldstone.raiseInfo(fail.responseText + e, true);
                }
            });
    },

    render: function() {
        this.$el.html(this.template());
        return this;
    },

    trimInputField: function(selector) {

        // remove leading/trailing spaces
        var trimmedContent = $(selector).val().trim();
        $(selector).val(trimmedContent);
    },

    template: _.template('' +
        '<div class="container">' +
        '<div class="row">' +

        // personal settings form
        '<div class="col-md-4 col-md-offset-2">' +
        '<form class="settings-form">' +
        '<h3>Update Personal Settings</h3>' +
        '<label for="inputUsername">Username</label>' +
        '<input name="username" type="text" class="form-control" placeholder="username" required>' +
        '<label for="inputFirstname">First name</label>' +
        '<input name="first_name" type="text" class="form-control" placeholder="First name" autofocus>' +
        '<label for="inputLastname">Last name</label>' +
        '<input name="last_name" type="text" class="form-control" placeholder="Last name">' +
        '<label for="inputEmail">Email</label>' +
        '<input name="email" type="email" class="form-control" placeholder="Email"><br>' +
        '<button name="submit" class="btn btn-lg btn-primary btn-block" type="submit">Update</button>' +
        '</form>' +
        '</div>' +

        // password reset form
        '<div class="col-md-4">' +
        '<form class="password-reset-form">' +
        '<h3>Change Password</h3>' +
        '<label for="inputCurrentPassword">Current password</label>' +
        '<input name="current_password" type="password" class="form-control" placeholder="Current password" required>' +
        '<label for="inputNewPassword">New password</label>' +
        '<input name="new_password" type="password" class="form-control" placeholder="New password" required><br>' +
        '<button name="submit" class="btn btn-lg btn-primary btn-block" type="submit">Change password</button>' +
        '</form>' +
        '</div>' +

        '</div>' +
        '</div>'
    )

});