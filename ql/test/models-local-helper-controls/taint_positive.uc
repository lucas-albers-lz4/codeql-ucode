import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen(request.args.cmd); }
const methods = { getFeatures: { call: function() {
  callPackageVersionCheck('netifd');
} } };
return methods;
