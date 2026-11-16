import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  obj.callPackageVersionCheck('netifd');
} } };
return methods;
