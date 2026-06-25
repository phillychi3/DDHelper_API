<script lang="ts">
	import { onMount } from 'svelte';
	import type { Company, CompanyCreate, CompanyUpdate, VTuber } from '$lib/api';
	import {
		getAllCompanies,
		createCompany,
		updateCompany,
		deleteCompany,
		getAllVTubers,
		batchAssignCompany
	} from '$lib/api';

	// State
	let companies = $state<Company[]>([]);
	let allVtubers = $state<VTuber[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	// Modal states
	let showCreateModal = $state(false);
	let showEditModal = $state(false);
	let showDeleteModal = $state(false);
	let showMembersModal = $state(false);
	let selectedCompany = $state<Company | null>(null);

	// Member management state
	let memberSearch = $state('');
	let selectedChannelIds = $state<Set<string>>(new Set());
	let savingMembers = $state(false);

	// Form data
	let createForm = $state<CompanyCreate>({ name: '', youtube: '', twitter: '' });
	let editForm = $state<CompanyUpdate>({ name: '', youtube: '', twitter: '' });

	// Filtered vtubers in the member modal
	let filteredVtubers = $derived(
		allVtubers.filter(
			(v) =>
				v.name.toLowerCase().includes(memberSearch.toLowerCase()) ||
				v.company.toLowerCase().includes(memberSearch.toLowerCase()) ||
				v.channel_id.toLowerCase().includes(memberSearch.toLowerCase())
		)
	);

	async function loadAll() {
		try {
			loading = true;
			error = null;
			[companies, allVtubers] = await Promise.all([getAllCompanies(), getAllVTubers()]);
		} catch (e) {
			error = e instanceof Error ? e.message : '載入失敗';
		} finally {
			loading = false;
		}
	}

	// Create company
	async function handleCreate() {
		try {
			await createCompany(createForm);
			showCreateModal = false;
			createForm = { name: '', description: '' };
			showSuccess('公司建立成功');
			await loadAll();
		} catch (e) {
			error = e instanceof Error ? e.message : '建立失敗';
		}
	}

	// Edit company
	function openEditModal(company: Company) {
		selectedCompany = company;
		editForm = { name: company.name, youtube: company.youtube, twitter: company.twitter };
		showEditModal = true;
	}

	async function handleEdit() {
		if (!selectedCompany) return;
		try {
			await updateCompany(selectedCompany.name, editForm);
			showEditModal = false;
			selectedCompany = null;
			showSuccess('公司更新成功');
			await loadAll();
		} catch (e) {
			error = e instanceof Error ? e.message : '更新失敗';
		}
	}

	// Delete company
	function openDeleteModal(company: Company) {
		selectedCompany = company;
		showDeleteModal = true;
	}

	async function handleDelete() {
		if (!selectedCompany) return;
		try {
			await deleteCompany(selectedCompany.name);
			showDeleteModal = false;
			selectedCompany = null;
			showSuccess('公司已刪除');
			await loadAll();
		} catch (e) {
			error = e instanceof Error ? e.message : '刪除失敗';
		}
	}

	// Manage members
	function openMembersModal(company: Company) {
		selectedCompany = company;
		memberSearch = '';
		// Pre-select vtubers already in this company
		selectedChannelIds = new Set(
			allVtubers.filter((v) => v.company === company.name).map((v) => v.channel_id)
		);
		showMembersModal = true;
	}

	function toggleVtuber(channelId: string) {
		const next = new Set(selectedChannelIds);
		if (next.has(channelId)) {
			next.delete(channelId);
		} else {
			next.add(channelId);
		}
		selectedChannelIds = next;
	}

	async function handleSaveMembers() {
		if (!selectedCompany) return;
		try {
			savingMembers = true;
			const result = await batchAssignCompany(
				selectedCompany.name,
				Array.from(selectedChannelIds)
			);
			showMembersModal = false;
			selectedCompany = null;
			showSuccess(`成員已更新：新增 ${result.assigned} 位，移除 ${result.unassigned} 位`);
			await loadAll();
		} catch (e) {
			error = e instanceof Error ? e.message : '儲存失敗';
		} finally {
			savingMembers = false;
		}
	}

	function showSuccess(msg: string) {
		successMsg = msg;
		setTimeout(() => (successMsg = null), 3000);
	}

	function closeAllModals() {
		showCreateModal = false;
		showEditModal = false;
		showDeleteModal = false;
		showMembersModal = false;
		selectedCompany = null;
		createForm = { name: '', youtube: '', twitter: '' };
		editForm = { name: '', youtube: '', twitter: '' };
	}

	onMount(() => {
		loadAll();
	});
</script>

<div class="min-h-screen bg-gray-50 p-8">
	<div class="max-w-5xl mx-auto">

		<div class="mb-8 flex items-center justify-between">
			<div>
				<h1 class="text-3xl font-bold text-gray-900 mb-2">公司管理面板</h1>
				<p class="text-gray-600">管理 VTuber 所屬公司與成員</p>
			</div>
			<a href="/" class="text-blue-600 hover:text-blue-800 text-sm">← 返回首頁</a>
		</div>

		{#if error}
			<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
				{error}
				<button onclick={() => (error = null)} class="float-right font-bold">×</button>
			</div>
		{/if}

		{#if successMsg}
			<div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
				{successMsg}
			</div>
		{/if}

		<div class="bg-white rounded-lg shadow p-4 mb-6 flex gap-4 items-center">
			<span class="text-gray-600 flex-1">共 {companies.length} 間公司</span>
			<button
				onclick={() => (showCreateModal = true)}
				class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
			>
				+ 新增公司
			</button>
			<button
				onclick={() => loadAll()}
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
		{:else if companies.length === 0}
			<div class="bg-white rounded-lg shadow p-12 text-center text-gray-500">
				暫無公司資料，請點擊「新增公司」開始
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				{#each companies as company}
					<div class="bg-white rounded-lg shadow p-6 flex flex-col gap-3">
						<div class="flex items-start justify-between">
							<div>
								<h2 class="text-xl font-bold text-gray-900">{company.name}</h2>
								<div class="flex gap-3 mt-1 flex-wrap">
									{#if company.youtube}
										<a href={company.youtube} target="_blank" rel="noreferrer" class="text-xs text-red-600 hover:underline">YouTube</a>
									{/if}
									{#if company.twitter}
										<a href={company.twitter} target="_blank" rel="noreferrer" class="text-xs text-sky-500 hover:underline">Twitter</a>
									{/if}
								</div>
							</div>
							<span class="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-1 rounded-full">
								{company.vtuber_count} 位 VTuber
							</span>
						</div>
						<div class="flex gap-2 pt-2 border-t border-gray-100">
							<button
								onclick={() => openMembersModal(company)}
								class="flex-1 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm font-medium"
							>
								管理成員
							</button>
							<button
								onclick={() => openEditModal(company)}
								class="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
							>
								編輯
							</button>
							<button
								onclick={() => openDeleteModal(company)}
								class="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm"
							>
								刪除
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<!-- Create Modal -->
{#if showCreateModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-md w-full p-6">
			<h2 class="text-2xl font-bold mb-6">新增公司</h2>
			<form onsubmit={(e) => { e.preventDefault(); handleCreate(); }} class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">公司名稱 *</label>
					<input
						type="text"
						bind:value={createForm.name}
						required
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">YouTube 頻道網址</label>
					<input
						type="url"
						bind:value={createForm.youtube}
						placeholder="https://www.youtube.com/@..."
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Twitter / X 網址</label>
					<input
						type="url"
						bind:value={createForm.twitter}
						placeholder="https://twitter.com/..."
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div class="flex justify-end gap-3 mt-6">
					<button type="button" onclick={closeAllModals} class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
						取消
					</button>
					<button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
						建立
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Edit Modal -->
{#if showEditModal && selectedCompany}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-md w-full p-6">
			<h2 class="text-2xl font-bold mb-6">編輯公司</h2>
			<form onsubmit={(e) => { e.preventDefault(); handleEdit(); }} class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">公司名稱 *</label>
					<input
						type="text"
						bind:value={editForm.name}
						required
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">YouTube 頻道網址</label>
					<input
						type="url"
						bind:value={editForm.youtube}
						placeholder="https://www.youtube.com/@..."
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Twitter / X 網址</label>
					<input
						type="url"
						bind:value={editForm.twitter}
						placeholder="https://twitter.com/..."
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<p class="text-xs text-gray-500">重新命名公司將同時更新所有隸屬此公司的 VTuber 資料。</p>
				<div class="flex justify-end gap-3 mt-6">
					<button type="button" onclick={closeAllModals} class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
						取消
					</button>
					<button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
						保存
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Delete Modal -->
{#if showDeleteModal && selectedCompany}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-md w-full p-6">
			<h2 class="text-xl font-bold mb-4">確認刪除</h2>
			<p class="text-gray-600 mb-2">
				你確定要刪除公司 <strong>{selectedCompany.name}</strong> 嗎？
			</p>
			<p class="text-sm text-red-600 mb-6">
				此操作將清空該公司所有 {selectedCompany.vtuber_count} 位 VTuber 的公司欄位，且無法撤銷。
			</p>
			<div class="flex justify-end gap-3">
				<button onclick={closeAllModals} class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
					取消
				</button>
				<button onclick={handleDelete} class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
					刪除
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Members Modal -->
{#if showMembersModal && selectedCompany}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] flex flex-col">
			<div class="p-6 border-b border-gray-200">
				<h2 class="text-2xl font-bold">管理成員 — {selectedCompany.name}</h2>
				<p class="text-sm text-gray-500 mt-1">
					勾選隸屬此公司的 VTuber，儲存後未勾選者將被移出公司。
				</p>
			</div>

			<div class="p-4 border-b border-gray-200">
				<div class="flex items-center gap-3">
					<input
						type="text"
						placeholder="搜索 VTuber..."
						bind:value={memberSearch}
						class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
					/>
					<span class="text-sm text-gray-500 whitespace-nowrap">
						已選 {selectedChannelIds.size} / {allVtubers.length}
					</span>
				</div>
			</div>

			<div class="overflow-y-auto flex-1 p-4">
				{#if filteredVtubers.length === 0}
					<p class="text-center text-gray-500 py-8">沒有找到 VTuber</p>
				{:else}
					<div class="space-y-2">
						{#each filteredVtubers as vtuber}
							<label
								class="flex items-center gap-3 p-3 rounded-lg cursor-pointer hover:bg-gray-50
									{selectedChannelIds.has(vtuber.channel_id) ? 'bg-blue-50 border border-blue-200' : 'border border-gray-100'}"
							>
								<input
									type="checkbox"
									checked={selectedChannelIds.has(vtuber.channel_id)}
									onchange={() => toggleVtuber(vtuber.channel_id)}
									class="h-4 w-4 text-blue-600 rounded"
								/>
								{#if vtuber.thumbnail}
									<img src={vtuber.thumbnail} alt={vtuber.name} class="h-8 w-8 rounded-full shrink-0" />
								{:else}
									<div class="h-8 w-8 rounded-full bg-gray-300 shrink-0"></div>
								{/if}
								<div class="flex-1 min-w-0">
									<div class="text-sm font-medium text-gray-900 truncate">{vtuber.name}</div>
									<div class="text-xs text-gray-500 truncate">
										{vtuber.channel_id}
										{#if vtuber.company && vtuber.company !== selectedCompany.name}
											<span class="ml-1 text-orange-500">（目前：{vtuber.company}）</span>
										{/if}
									</div>
								</div>
								<span class="text-xs px-2 py-0.5 rounded-full shrink-0
									{vtuber.platform === 'youtube' ? 'bg-red-100 text-red-700' : 'bg-purple-100 text-purple-700'}">
									{vtuber.platform}
								</span>
							</label>
						{/each}
					</div>
				{/if}
			</div>

			<div class="p-4 border-t border-gray-200 flex justify-end gap-3">
				<button onclick={closeAllModals} class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
					取消
				</button>
				<button
					onclick={handleSaveMembers}
					disabled={savingMembers}
					class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
				>
					{savingMembers ? '儲存中...' : '儲存成員'}
				</button>
			</div>
		</div>
	</div>
{/if}
