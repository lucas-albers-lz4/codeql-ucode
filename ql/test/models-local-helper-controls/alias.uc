import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  let alias = callPackageVersionCheck; callPackageVersionCheck('netifd');
} } };
return methods;
