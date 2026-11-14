'use strict';
import { popen } from 'fs';
let shellquote = s => s;
const methods = { probe: { call: function(request) {
	popen(`echo ${shellquote(request.args.value)} done`);
} } };
return methods;
