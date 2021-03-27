var iterations = 0;
while(rs.status()['myState'] != 1) {
		sleep(3000);
		iterations++;
		if (iterations == 100) {
			throw new Error("Exceeded iterations limit.");
		}
	}
