function ubus_call(object, method, args) { return ubus.call(object, method, args); }
function other(ubus_call) { ubus_call('uci', 'commit', {}); }
