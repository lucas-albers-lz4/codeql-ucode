import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  callPackageVersionCheck = null; callPackageVersionCheck('netifd');
} } };
return methods;
