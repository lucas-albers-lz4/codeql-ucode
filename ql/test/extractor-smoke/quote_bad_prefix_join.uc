'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`echo prefix${shellquote(request.args.value)} done`);
} } };
return methods;
