import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  try { throw 1; } catch (callPackageVersionCheck) { callPackageVersionCheck('netifd'); }
} } };
return methods;
