import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  (function(callPackageVersionCheck) { callPackageVersionCheck('netifd'); })(null);
} } };
return methods;
