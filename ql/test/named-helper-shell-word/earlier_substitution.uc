'use strict';

import { popen } from 'fs';

function run_command(section) {
	return popen(`lldpcli ${mode} show ${section}`, 'r');
}

const methods = {
	getStatus: {
		call: function(request) {
			return run_command(request.args.section);
		}
	}
};

return { 'luci.synthetic': methods };
