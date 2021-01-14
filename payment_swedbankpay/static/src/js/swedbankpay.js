odoo.define('payment_swedbankpay.swedbankpay', function (require) {
    "use strict";
    console.log("~ inside")
    var ajax = require('web.ajax');
    var config = require('web.config');
    var core = require('web.core');
    var dom = require('web.dom');
    var Dialog = require("web.Dialog");
    var Widget = require("web.Widget");
    var rpc = require("web.rpc");
    var _t = core._t;

    // document.getElementById("o_payment_form_pay").addEventListener("click", function(){
    //     console.log("~ o_payment_form_pay clicked!")
    // })

    // check if there is an o_payment button
    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
    }
    
    function myFunction() {
        console.log("my function")
        this._rpc('/payment/swedbankpay/testing', {
            acquirer_id: "TESTING",
            so_id: "so_id_test"
        }).then(function(data) {
            console.log(`~then=${data}`);
            if(data!=="false"){
                window.location.href = data;
                window.location.replace(data);
            }
            // data will have the redirection url here.
        }).done(function(data) {
            console.log(`~done=${data}`);
        });
    }

    $(".o_payment_form").attr("action", "/payment/swedbankpay/testing")

    // is activated when there is a click on the button 
    // and the provier that is choosen is swedbankpay

    // maybe this is called two times, i dont know....
    var observer = new MutationObserver(function(mutations, observer) {
        for(var i=0; i<mutations.length; ++i) {
            for(var j=0; j<mutations[i].addedNodes.length; ++j) {
                if(mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') == 'swedbankpay') {
                    console.log("~ mutation");
                    display_form($(mutations[i].addedNodes[j]));
                }
            }
        }
    });

    
    function display_form(provider_form){

        var payment_form = $('.o_payment_form');
        if(!payment_form.find('i').length)
            payment_form.append('<i class="fa fa-spinner fa-spin"/>');
            payment_form.attr('disabled','disabled');

        var payment_tx_url = payment_form.find('input[name="prepare_tx_url"]').val();
        console.log(`payment_tx_url = ${payment_tx_url}`);

        

        var get_input_value = function(name) {
            return provider_form.find('input[name="' + name + '"]').val();
        }

        var invoice_number = parseInt(provider_form.find('#acquirer_stripe').val());

        console.log(provider_form.find('#acquirer_stripe').val())
        console.log(get_input_value("test"))

        // call to
        // '/shop/payment/transaction/swedbankpay/<int:so_id>', (with sale_order_id)
        //~ this._rpc('/payment/swedbankpay/testing', {
            //~ acquirer_id: "TESTING",
            //~ so_id: "so_id_test"
        //~ }).then(function(data) {
            //~ console.log(`~then=${data}`);
            //~ if(data!=="false"){
                //~ window.location.href = data;
                //~ window.location.replace(data);
            //~ }
            //~ // data will have the redirection url here.
        //~ }).done(function(data) {
            //~ console.log(`~done=${data}`);
        //~ });
    }

    //~ console.log("~ start mutation!");
    //~ observer.observe(document.body, {childList: true});
});
