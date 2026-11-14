'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`ash -c ${shellquote(request.args.value)} ignored`);
} } };
return methods;
