function ubus_call(object, method, args) { return ubus.call(method, object, args); }
ubus_call('uci', 'commit', {});
