import { popen } from 'fs';
function callPackageVersionCheck(pkg) { popen('true'); }
const methods = { getFeatures: { call: function() {
  let f = () => callPackageVersionCheck('netifd'); callPackageVersionCheck = null; f();
} } };
return methods;
