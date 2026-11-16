import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  consume(callPackageVersionCheck);
  callPackageVersionCheck('netifd');
} } };
return methods;
