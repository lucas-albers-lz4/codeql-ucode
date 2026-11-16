import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  let callPackageVersionCheck = callPackageVersionCheck('netifd');
} } };
return methods;
