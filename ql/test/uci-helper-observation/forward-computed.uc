function ubus_call(object, method, args) { return ubus['call'](object, method, args); }
ubus_call('uci', 'commit', {});
