function ubus_call(object, method, args) {
  function inner(object) { return ubus.call(object, method, args); }
  return inner(object);
}
ubus_call('uci', 'commit', {});
