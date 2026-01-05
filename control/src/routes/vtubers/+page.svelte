<script lang="ts">
	import { onMount } from 'svelte';
	import type { VTuber, VTuberCreate, VTuberUpdate } from '$lib/api';
	import { getAllVTubers, createVTuber, updateVTuber, deleteVTuber } from '$lib/api';

	// State
	let vtubers = $state<VTuber[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');

	// Modal states
	let showCreateModal = $state(false);
	let showEditModal = $state(false);
	let showDeleteModal = $state(false);
	let selectedVTuber = $state<VTuber | null>(null);

	// Scroll position state
	let savedScrollPosition = $state(0);

	// Form data
	let formData = $state<VTuberCreate>({
		name: '',
		channel_id: '',
		channel_url: '',
		platform: 'youtube',
		company: '',
		country: '',
		subscriber_count: 0,
		view_count: 0,
		video_count: 0,
		activity_status: 'active',
		debut_date: '',
		thumbnail: ''
	});

	// Filtered vtubers
	let filteredVTubers = $derived(
		vtubers.filter(
			(v) =>
				v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				v.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
				v.channel_id.toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	// Save scroll position
	function saveScrollPosition() {
		savedScrollPosition = window.scrollY || window.pageYOffset;
	}

	// Restore scroll position
	function restoreScrollPosition() {
		if (savedScrollPosition > 0) {
			setTimeout(() => {
				window.scrollTo(0, savedScrollPosition);
				savedScrollPosition = 0;
			}, 50);
		}
	}

	// Load VTubers
	async function loadVTubers(restoreScroll = false) {
		try {
			loading = true;
			error = null;
			vtubers = await getAllVTubers();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load VTubers';
		} finally {
			loading = false;
			if (restoreScroll) {
				restoreScrollPosition();
			}
		}
	}

	// Create VTuber
	async function handleCreate() {
		try {
			await createVTuber(formData);
			showCreateModal = false;
			resetForm();
			await loadVTubers();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create VTuber';
		}
	}

	// Edit VTuber
	function openEditModal(vtuber: VTuber) {
		// Validate that channel_id exists
		if (!vtuber.channel_id) {
			error = `無法編輯：VTuber "${vtuber.name}" 的 channel_id 為空`;
			console.error('Invalid VTuber data:', vtuber);
			return;
		}

		saveScrollPosition();
		selectedVTuber = vtuber;
		formData = { ...vtuber };
		showEditModal = true;
	}

	async function handleEdit() {
		if (!selectedVTuber) return;

		try {
			const updateData: VTuberUpdate = {
				name: formData.name,
				channel_url: formData.channel_url,
				platform: formData.platform,
				company: formData.company,
				country: formData.country,
				subscriber_count: formData.subscriber_count,
				view_count: formData.view_count,
				video_count: formData.video_count,
				activity_status: formData.activity_status,
				debut_date: formData.debut_date,
				thumbnail: formData.thumbnail
			};

			await updateVTuber(selectedVTuber.channel_id, updateData);
			showEditModal = false;
			resetForm();
			await loadVTubers(true);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update VTuber';
		}
	}


	function openDeleteModal(vtuber: VTuber) {

		if (!vtuber.channel_id) {
			error = `無法刪除：VTuber "${vtuber.name}" 的 channel_id 為空`;
			console.error('Invalid VTuber data:', vtuber);
			return;
		}

		saveScrollPosition();
		selectedVTuber = vtuber;
		showDeleteModal = true;
	}

	async function handleDelete() {
		if (!selectedVTuber) return;

		try {
			await deleteVTuber(selectedVTuber.channel_id);
			showDeleteModal = false;
			selectedVTuber = null;
			await loadVTubers(true);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete VTuber';
		}
	}

	function resetForm() {
		formData = {
			name: '',
			channel_id: '',
			channel_url: '',
			platform: 'youtube',
			company: '',
			country: '',
			subscriber_count: 0,
			view_count: 0,
			video_count: 0,
			activity_status: 'active',
			debut_date: '',
			thumbnail: ''
		};
		selectedVTuber = null;
	}

	function closeAllModals() {
		showCreateModal = false;
		showEditModal = false;
		showDeleteModal = false;
		resetForm();
	}

	onMount(() => {
		loadVTubers();
	});
</script>

<div class="min-h-screen bg-gray-50 p-8">
	<div class="max-w-7xl mx-auto">

		<div class="mb-8">
			<h1 class="text-3xl font-bold text-gray-900 mb-2">VTuber 管理面板</h1>
			<p class="text-gray-600">管理你的 VTuber 資料庫</p>
		</div>


		{#if error}
			<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
				{error}
				<button onclick={() => (error = null)} class="float-right font-bold">×</button>
			</div>
		{/if}


		<div class="bg-white rounded-lg shadow p-4 mb-6 flex gap-4 items-center">
			<input
				type="text"
				placeholder="搜索 VTuber..."
				bind:value={searchQuery}
				class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
			/>
			<button
				onclick={() => (showCreateModal = true)}
				class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
			>
				+ 新增 VTuber
			</button>
			<button
				onclick={() => loadVTubers()}
				class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
			>
				刷新
			</button>
		</div>


		{#if loading}
			<div class="text-center py-12">
				<div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
				<p class="mt-4 text-gray-600">載入中...</p>
			</div>
		{:else}

			<div class="bg-white rounded-lg shadow overflow-hidden">
				<table class="min-w-full divide-y divide-gray-200">
					<thead class="bg-gray-50">
						<tr>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">縮圖</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">名稱</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">公司</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">平台</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">訂閱數</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">狀態</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
						</tr>
					</thead>
					<tbody class="bg-white divide-y divide-gray-200">
						{#each filteredVTubers as vtuber}
							<tr class="hover:bg-gray-50">
								<td class="px-6 py-4 whitespace-nowrap">
									{#if vtuber.thumbnail}
										<img src={vtuber.thumbnail} alt={vtuber.name} class="h-10 w-10 rounded-full" />
									{:else}
										<div class="h-10 w-10 rounded-full bg-gray-300"></div>
									{/if}
								</td>
								<td class="px-6 py-4 whitespace-nowrap">
									<div class="text-sm font-medium text-gray-900">{vtuber.name}</div>
									<div class="text-sm text-gray-500">{vtuber.channel_id}</div>
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{vtuber.company || '-'}</td>
								<td class="px-6 py-4 whitespace-nowrap">
									<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
										{vtuber.platform === 'youtube' ? 'bg-red-100 text-red-800' : 'bg-purple-100 text-purple-800'}">
										{vtuber.platform}
									</span>
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
									{vtuber.subscriber_count.toLocaleString()}
								</td>
								<td class="px-6 py-4 whitespace-nowrap">
									<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
										{vtuber.activity_status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
										{vtuber.activity_status}
									</span>
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
									<button
										onclick={() => openEditModal(vtuber)}
										class="text-blue-600 hover:text-blue-900 mr-4"
									>
										編輯
									</button>
									<button
										onclick={() => openDeleteModal(vtuber)}
										class="text-red-600 hover:text-red-900"
									>
										刪除
									</button>
								</td>
							</tr>
						{:else}
							<tr>
								<td colspan="7" class="px-6 py-12 text-center text-gray-500">
									{searchQuery ? '沒有找到匹配的 VTuber' : '暫無 VTuber 數據'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<div class="mt-4 text-sm text-gray-600">
				共 {filteredVTubers.length} / {vtubers.length} 個 VTuber
			</div>
		{/if}
	</div>
</div>


{#if showCreateModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
			<div class="p-6">
				<h2 class="text-2xl font-bold mb-6">新增 VTuber</h2>
				<form onsubmit={(e) => { e.preventDefault(); handleCreate(); }} class="space-y-4">
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">名稱 *</label>
							<input
								type="text"
								bind:value={formData.name}
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">Channel ID *</label>
							<input
								type="text"
								bind:value={formData.channel_id}
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">頻道 URL *</label>
						<input
							type="url"
							bind:value={formData.channel_url}
							required
							class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">平台</label>
							<select
								bind:value={formData.platform}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							>
								<option value="youtube">YouTube</option>
								<option value="twitch">Twitch</option>
							</select>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">狀態</label>
							<select
								bind:value={formData.activity_status}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							>
								<option value="active">活躍</option>
								<option value="inactive">不活躍</option>
								<option value="graduated">畢業</option>
							</select>
						</div>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">公司</label>
							<input
								type="text"
								bind:value={formData.company}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">國家</label>
							<input
								type="text"
								bind:value={formData.country}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">縮圖 URL</label>
						<input
							type="url"
							bind:value={formData.thumbnail}
							class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<div class="grid grid-cols-3 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">訂閱數</label>
							<input
								type="number"
								bind:value={formData.subscriber_count}
								min="0"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">觀看數</label>
							<input
								type="number"
								bind:value={formData.view_count}
								min="0"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">影片數</label>
							<input
								type="number"
								bind:value={formData.video_count}
								min="0"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">出道日期</label>
						<input
							type="date"
							bind:value={formData.debut_date}
							class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<div class="flex justify-end gap-3 mt-6">
						<button
							type="button"
							onclick={closeAllModals}
							class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
						>
							取消
						</button>
						<button
							type="submit"
							class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
						>
							創建
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
{/if}


{#if showEditModal && selectedVTuber}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
			<div class="p-6">
				<h2 class="text-2xl font-bold mb-6">編輯 VTuber</h2>
				<form onsubmit={(e) => { e.preventDefault(); handleEdit(); }} class="space-y-4">
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">名稱 *</label>
							<input
								type="text"
								bind:value={formData.name}
								required
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">Channel ID</label>
							<input
								type="text"
								value={selectedVTuber.channel_id}
								disabled
								class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">頻道 URL *</label>
						<input
							type="url"
							bind:value={formData.channel_url}
							required
							class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">平台</label>
							<select
								bind:value={formData.platform}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							>
								<option value="youtube">YouTube</option>
								<option value="twitch">Twitch</option>
							</select>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">狀態</label>
							<select
								bind:value={formData.activity_status}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							>
								<option value="active">活躍</option>
								<option value="inactive">不活躍</option>
								<option value="graduated">畢業</option>
							</select>
						</div>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">公司</label>
							<input
								type="text"
								bind:value={formData.company}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">國家</label>
							<input
								type="text"
								bind:value={formData.country}
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">縮圖 URL</label>
						<input
							type="url"
							bind:value={formData.thumbnail}
							class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<div class="grid grid-cols-3 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">訂閱數</label>
							<input
								type="number"
								bind:value={formData.subscriber_count}
								min="0"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">觀看數</label>
							<input
								type="number"
								bind:value={formData.view_count}
								min="0"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">影片數</label>
							<input
								type="number"
								bind:value={formData.video_count}
								min="0"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">出道日期</label>
						<input
							type="date"
							bind:value={formData.debut_date}
							class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<div class="flex justify-end gap-3 mt-6">
						<button
							type="button"
							onclick={closeAllModals}
							class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
						>
							取消
						</button>
						<button
							type="submit"
							class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
						>
							保存
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
{/if}


{#if showDeleteModal && selectedVTuber}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-md w-full p-6">
			<h2 class="text-xl font-bold mb-4">確認刪除</h2>
			<p class="text-gray-600 mb-6">
				你確定要刪除 <strong>{selectedVTuber.name}</strong> 嗎？此操作無法撤銷。
			</p>
			<div class="flex justify-end gap-3">
				<button
					onclick={closeAllModals}
					class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
				>
					取消
				</button>
				<button
					onclick={handleDelete}
					class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
				>
					刪除
				</button>
			</div>
		</div>
	</div>
{/if}
