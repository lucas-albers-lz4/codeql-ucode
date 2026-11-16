import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  (function(callPackageVersionCheck) { (function() { callPackageVersionCheck('netifd'); })(); })(null);
} } };
return methods;
