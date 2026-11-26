'use strict';
import { popen } from 'fs';
function shell_quote(s) {
  if (s == null || s == '') return "''";
  return "'" + replace(s, "'", "'\t''") + "'";
}
const methods = {};
methods.probe = {
  args: { form_data: {} },
  call: function(payload) {
    const form_data = payload.args.form_data;
    let words = [];
    const endpoint = trim(form_data.endpoint) || '';
    if (endpoint != '') {
      push(words, '--endpoint ' + shell_quote(endpoint));
    }
    let login_cmd = 'meshctl connect ' + join(' ', words);
    popen('/bin/sh -c "' + login_cmd + ' &"', 'r');
  }
};
return methods;
