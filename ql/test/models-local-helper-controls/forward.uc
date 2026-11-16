import { popen } from 'fs';
const methods = { getFeatures: { call: function() { callPackageVersionCheck('netifd'); } } };
function callPackageVersionCheck(pkg) { popen('true'); }
return methods;
