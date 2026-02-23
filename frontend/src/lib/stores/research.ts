import { writable } from 'svelte/store';

export interface ResearchStep {
	message: string;
	completed: boolean;
}

export interface ResearchState {
	activeTaskId: string | null;
	progress: number;
	currentStep: string;
	steps: ResearchStep[];
}

const initialState: ResearchState = {
	activeTaskId: null,
	progress: 0,
	currentStep: '',
	steps: []
};

export const researchState = writable<ResearchState>(initialState);

export function resetResearch() {
	researchState.set(initialState);
}
