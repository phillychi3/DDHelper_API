// API base URL - adjust based on your environment
const API_BASE_URL = 'http://localhost:7600';

// VTuber types
export interface VTuber {
	channel_id: string;
	name: string;
	company: string;
	country: string;
	channel_url: string;
	platform: string;
	subscriber_count: number;
	view_count: number;
	video_count: number;
	activity_status: string;
	debut_date: string;
	thumbnail: string;
}

export interface VTuberCreate {
	name: string;
	channel_id: string;
	channel_url: string;
	platform?: string;
	company?: string;
	country?: string;
	subscriber_count?: number;
	view_count?: number;
	video_count?: number;
	activity_status?: string;
	debut_date?: string;
	thumbnail?: string;
}

export interface VTuberUpdate {
	name?: string;
	channel_url?: string;
	platform?: string;
	company?: string;
	country?: string;
	subscriber_count?: number;
	view_count?: number;
	video_count?: number;
	activity_status?: string;
	debut_date?: string;
	thumbnail?: string;
}

// API functions
export async function getAllVTubers(): Promise<VTuber[]> {
	const response = await fetch(`${API_BASE_URL}/allvtuber`);
	if (!response.ok) {
		throw new Error('Failed to fetch VTubers');
	}
	return response.json();
}

export async function getVTuber(channelId: string): Promise<VTuber> {
	const response = await fetch(`${API_BASE_URL}/vtuber/${channelId}`);
	if (!response.ok) {
		throw new Error('Failed to fetch VTuber');
	}
	return response.json();
}

export async function createVTuber(vtuber: VTuberCreate): Promise<{ message: string; channel_id: string }> {
	const response = await fetch(`${API_BASE_URL}/vtuber`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(vtuber)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to create VTuber');
	}

	return response.json();
}

export async function updateVTuber(
	channelId: string,
	vtuber: VTuberUpdate
): Promise<{ message: string; channel_id: string }> {
	if (!channelId) {
		throw new Error('Channel ID is required for update');
	}

	const response = await fetch(`${API_BASE_URL}/vtuber/${encodeURIComponent(channelId)}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(vtuber)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to update VTuber');
	}

	return response.json();
}

export async function deleteVTuber(channelId: string): Promise<{ message: string; channel_id: string }> {
	if (!channelId) {
		throw new Error('Channel ID is required for delete');
	}

	const response = await fetch(`${API_BASE_URL}/vtuber/${encodeURIComponent(channelId)}`, {
		method: 'DELETE'
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to delete VTuber');
	}

	return response.json();
}
