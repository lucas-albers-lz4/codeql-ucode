function ubus_call(object, method, args) { return ubus.call(object, method, args); }
ubus_call(object, 'commit', {});
ubus_call('uci', method, {});
ubus_call('uci', 'com' + 'mit', {});
