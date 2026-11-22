function ubus_call(object, method, args) { return ubus.call(object, unknown, args); }
ubus_call('uci', 'commit', {});
