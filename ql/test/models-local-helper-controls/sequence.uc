import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  (0, callPackageVersionCheck)('netifd');
} } };
return methods;
