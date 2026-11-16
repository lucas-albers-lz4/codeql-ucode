import { popen } from 'fs';
const methods = { getFeatures: { call: function() { callPackageVersionCheck('netifd'); } } };
return methods;
