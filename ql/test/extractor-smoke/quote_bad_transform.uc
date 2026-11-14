'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`echo ${replace(shellquote(request.args.value), /'/g, '')} done`);
} } };
return methods;
