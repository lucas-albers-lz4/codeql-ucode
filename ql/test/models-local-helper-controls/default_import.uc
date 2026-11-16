import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
import callPackageVersionCheck from 'other';
const methods = { getFeatures: { call: function() {
  callPackageVersionCheck('netifd');
} } };
return methods;
