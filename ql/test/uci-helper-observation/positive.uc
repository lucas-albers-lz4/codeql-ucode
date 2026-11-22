function ubus_call(object, method, args) {
  return ubus.call(object, method, args);
}
ubus_call('uci', 'commit', {});
ubus_call('uci', 'changes', {});
ubus_call('session', 'set', {});
ubus.call('uci', unknown, {});
ubus[unknown]('uci', 'commit', {});
let property = ubus.call;
