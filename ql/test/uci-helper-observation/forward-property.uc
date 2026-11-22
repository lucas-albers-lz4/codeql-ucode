function ubus_call(object, method, args) { return ubus.call; }
ubus_call('uci', 'commit', {});
