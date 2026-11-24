'use strict';
import { popen } from 'fs';
function shell_quote(s) {
  if (s == null || s == '') return "''";
  return "'" + replace(s, "'", "'\\''") + "'";
}
const methods = {};
methods.probe = {
  args: { form_data: {} },
  call: function(request) {
    const form_data = request.args.form_data;
    let loginargs = [];
    const unused_loginserver = trim(form_data.loginserver) || '';
    push(loginargs, '--login-server ' + shell_quote('https://login.tailscale.com'));
    let login_cmd = 'tailscale login ' + join(' ', loginargs);
    popen('/bin/sh -c "' + login_cmd + ' &"', 'r');
  }
};
return methods;
