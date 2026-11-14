'use strict';
import { popen } from 'fs';
function shellquote(s) { return s; }
const methods = { probe: { call: function(request) {
	popen(`echo ${shellquote(request.args.value)} done`);
} } };
return methods;
