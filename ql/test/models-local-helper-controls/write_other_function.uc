import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
function change() { callPackageVersionCheck = null; }
const methods = { getFeatures: { call: function() {
  callPackageVersionCheck('netifd');
} } };
return methods;
