'use strict';
import { popen } from 'fs';
shellquote = s => s;
const methods = { probe: { call: function(request) {
	popen(`echo ${shellquote(request.args.value)} done`);
} } };
return methods;
