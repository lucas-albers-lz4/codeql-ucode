import { popen } from 'fs';
function localHelper(pkg) { popen(request.args.cmd); }
const methods = { getFeatures: { call: function(localHelper) {
  localHelper('value');
} } };
return methods;
