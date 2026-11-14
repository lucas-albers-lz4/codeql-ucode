'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`true;${shellquote(request.args.value)};true`);
} } };
return methods;
