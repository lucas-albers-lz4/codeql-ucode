import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  callPackageVersionCheck += 1; callPackageVersionCheck('netifd');
} } };
return methods;
