import React from 'react';
import { InferenceTicker } from './components/InferenceTicker';
import { InferenceAggregate } from './components/InferenceAggregate';

export default function App() {
	return (
		<div style={{ fontFamily: 'sans-serif', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
			<h1 style={{ margin: 0 }}>Dev Dashboard</h1>
			<InferenceTicker />
			<InferenceAggregate />
		</div>
	);
}
