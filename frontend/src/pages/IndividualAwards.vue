<template>
  <div class="min-h-screen bg-gray-50 px-6 py-8">
    <!-- Page Header -->
    <div class="mb-8">
      <div class="bg-white rounded-lg p-6 shadow-sm border">
        <div class="flex justify-between items-center">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 mb-2">My Individual Awards</h1>
            <p class="text-gray-600">View personal certificates and recognition</p>
          </div>
          <div>
            <Button @click="loadAwards" :loading="isRefreshing" size="sm" variant="outline">
              <template #prefix>
                <FeatherIcon name="refresh-cw" class="h-4 w-4" />
              </template>
              Refresh
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Filter Section -->
    <div class="bg-white rounded-lg shadow-sm border p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Filter Awards</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Year -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Year</label>
          <Dropdown :options="yearOptions" v-model="filterYear">
            <template #default="{ open }">
              <Button :label="filterYear || 'All Years'" class="w-full justify-between">
                <template #suffix>
                  <FeatherIcon :name="open ? 'chevron-up' : 'chevron-down'" class="h-4 text-gray-600" />
                </template>
              </Button>
            </template>
          </Dropdown>
        </div>

        <!-- Category -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Category</label>
          <Dropdown :options="categoryOptions" v-model="filterCategory">
            <template #default="{ open }">
              <Button :label="filterCategory || 'All Categories'" class="w-full justify-between">
                <template #suffix>
                  <FeatherIcon :name="open ? 'chevron-up' : 'chevron-down'" class="h-4 text-gray-600" />
                </template>
              </Button>
            </template>
          </Dropdown>
        </div>

        <!-- Clear -->
        <div class="flex items-end">
          <Button @click="clearFilters" class="w-full" variant="outline">
            <template #prefix>
              <FeatherIcon name="x-circle" class="h-4 w-4" />
            </template>
            Clear Filters
          </Button>
        </div>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
      <div class="flex items-start">
        <FeatherIcon name="alert-circle" class="h-5 w-5 text-red-600 mt-0.5 mr-3" />
        <div>
          <h3 class="text-sm font-medium text-red-800">Error Loading Awards</h3>
          <p class="text-sm text-red-700 mt-1">{{ errorMessage }}</p>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p class="text-gray-600">Loading your awards...</p>
    </div>

    <!-- Awards Grid -->
    <div v-else-if="filteredAwards.length > 0" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div
        v-for="award in filteredAwards"
        :key="award.name"
        class="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow"
      >
        <h3 class="text-lg font-semibold text-gray-900 mb-1">{{ award.title }}</h3>
        <p class="text-sm text-gray-600 mb-2">{{ award.date }}</p>
        <p class="text-sm text-gray-700 mb-4">{{ award.description }}</p>

        <div class="flex justify-between items-center border-t pt-4">
          <span class="text-xs text-gray-500">{{ award.category }}</span>
          <Button size="sm" v-if="award.file" @click="downloadCertificate(award)">
            <template #prefix>
              <FeatherIcon name="download" class="h-4 w-4" />
            </template>
            Certificate
          </Button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <div class="bg-white rounded-lg p-8 shadow-sm border">
        <FeatherIcon name="award" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No Awards Found</h3>
        <p class="text-gray-600">You don't have any individual awards yet.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Button, Dropdown, FeatherIcon, call } from 'frappe-ui'

const isLoading = ref(false)
const isRefreshing = ref(false)
const allAwards = ref([])
const filterYear = ref('')
const filterCategory = ref('')
const errorMessage = ref('')

const yearOptions = computed(() => {
  const years = [...new Set(allAwards.value.map(a => a.year))].sort()
  return [{ label: 'All Years', value: '', onClick: () => filterYear.value = '' }]
    .concat(years.map(y => ({ label: y, value: y, onClick: () => filterYear.value = y })))
})

const categoryOptions = [
  { label: 'All Categories', value: '', onClick: () => filterCategory.value = '' },
  { label: 'Academic', value: 'Academic', onClick: () => filterCategory.value = 'Academic' },
  { label: 'Sports', value: 'Sports', onClick: () => filterCategory.value = 'Sports' },
  { label: 'Leadership', value: 'Leadership', onClick: () => filterCategory.value = 'Leadership' },
  { label: 'Behavioural', value: 'Behavioural', onClick: () => filterCategory.value = 'Behavioural' },
]

const filteredAwards = computed(() => {
  return allAwards.value.filter(a =>
    (!filterYear.value || a.year === filterYear.value) &&
    (!filterCategory.value || a.category === filterCategory.value)
  )
})

const loadAwards = async () => {
  isLoading.value = true
  isRefreshing.value = true
  errorMessage.value = ''
  
  try {
    const res = await call('piamtech_frappe_education.school_portal_api.get_individual_awards')
    
    allAwards.value = (res || []).map(a => ({
      name: a.name,
      title: a.certificate_title,
      date: a.certificate_date,
      description: a.description,
      category: a.certificate_type,
      year: a.academic_year,
      file: a.certificate_file
    }))
  } catch (error) {
    console.error('Error loading awards:', error)
    errorMessage.value = error.message || 'Failed to load awards. Please try again.'
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

const clearFilters = () => {
  filterYear.value = ''
  filterCategory.value = ''
}

const downloadCertificate = async (award) => {
  try {
    const res = await call('piamtech_frappe_education.school_portal_api.download_certificate', {
      award_name: award.name
    })
    
    if (res.file_url) {
      window.open(res.file_url, '_blank')
    }
  } catch (error) {
    console.error('Error downloading certificate:', error)
    alert('Error downloading certificate: ' + error.message)
  }
}

onMounted(() => {
  loadAwards()
})
</script>