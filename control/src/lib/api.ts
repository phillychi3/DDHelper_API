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

// Company types
export interface Company {
	name: string;
	youtube: string;
	twitter: string;
	vtuber_count: number;
}

export interface CompanyCreate {
	name: string;
	youtube?: string;
	twitter?: string;
}

export interface CompanyUpdate {
	name?: string;
	youtube?: string;
	twitter?: string;
}

// Company API functions
export async function getAllCompanies(): Promise<Company[]> {
	const response = await fetch(`${API_BASE_URL}/companies`);
	if (!response.ok) throw new Error('Failed to fetch companies');
	return response.json();
}

export async function createCompany(company: CompanyCreate): Promise<{ message: string; name: string }> {
	const response = await fetch(`${API_BASE_URL}/company`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(company)
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to create company');
	}
	return response.json();
}

export async function updateCompany(
	name: string,
	data: CompanyUpdate
): Promise<{ message: string; name: string }> {
	const response = await fetch(`${API_BASE_URL}/company/${encodeURIComponent(name)}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to update company');
	}
	return response.json();
}

export async function deleteCompany(name: string): Promise<{ message: string; name: string }> {
	const response = await fetch(`${API_BASE_URL}/company/${encodeURIComponent(name)}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to delete company');
	}
	return response.json();
}

export async function getCompanyVtubers(name: string): Promise<VTuber[]> {
	const response = await fetch(`${API_BASE_URL}/company/${encodeURIComponent(name)}/vtubers`);
	if (!response.ok) throw new Error('Failed to fetch company vtubers');
	return response.json();
}

// Country types
export interface Country {
	name: string;
	vtuber_count: number;
}

export interface CountryCreate {
	name: string;
}

export interface CountryUpdate {
	name?: string;
}

// Country API functions
export async function getAllCountries(): Promise<Country[]> {
	const response = await fetch(`${API_BASE_URL}/countries`);
	if (!response.ok) throw new Error('Failed to fetch countries');
	return response.json();
}

export async function createCountry(name: string): Promise<{ message: string; name: string }> {
	const response = await fetch(`${API_BASE_URL}/country`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name })
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to create country');
	}
	return response.json();
}

export async function updateCountry(
	name: string,
	newName: string
): Promise<{ message: string; name: string }> {
	const response = await fetch(`${API_BASE_URL}/country/${encodeURIComponent(name)}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name: newName })
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to update country');
	}
	return response.json();
}

export async function deleteCountry(name: string): Promise<{ message: string; name: string }> {
	const response = await fetch(`${API_BASE_URL}/country/${encodeURIComponent(name)}`, {
		method: 'DELETE'
	});
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to delete country');
	}
	return response.json();
}

export async function batchAssignCountry(
	countryName: string,
	channelIds: string[]
): Promise<{ message: string; assigned: number; unassigned: number }> {
	const response = await fetch(
		`${API_BASE_URL}/country/${encodeURIComponent(countryName)}/vtubers/batch`,
		{
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ channel_ids: channelIds })
		}
	);
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to batch assign country');
	}
	return response.json();
}

export async function batchAssignCompany(
	companyName: string,
	channelIds: string[]
): Promise<{ message: string; assigned: number; unassigned: number }> {
	const response = await fetch(
		`${API_BASE_URL}/company/${encodeURIComponent(companyName)}/vtubers/batch`,
		{
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ channel_ids: channelIds })
		}
	);
	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to batch assign company');
	}
	return response.json();
}
