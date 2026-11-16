import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  try { fail(1); } catch (callPackageVersionCheck) { callPackageVersionCheck('netifd'); }
} } };
return methods;
