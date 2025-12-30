<template>
  <div class="min-h-screen bg-gray-50 px-6 py-8">
    <!-- Page Header -->
    <div class="mb-8">
      <div class="bg-white rounded-lg p-6 shadow-sm border">
        <div class="flex justify-between items-center">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 mb-2">My Academic Reports</h1>
            <p class="text-gray-600">View and download your term reports</p>
          </div>
          <div class="flex space-x-2">
            <Button @click="loadReports" :loading="isRefreshing" size="sm" variant="outline">
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
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Filter Reports</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">

         <!-- Class Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Class</label>
          <Dropdown :options="programFilterOptions" v-model="filterProgram">
            <template #default="{ open }">
              <Button 
                :label="filterProgram || 'All Classes'"
                class="w-full justify-between"
              >
                <template #suffix>
                  <FeatherIcon
                    :name="open ? 'chevron-up' : 'chevron-down'"
                    class="h-4 text-gray-600"
                  />
                </template>
              </Button>
            </template>
          </Dropdown>
        </div>


        <!-- Academic Year Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Academic Year</label>
          <Dropdown :options="academicYearFilterOptions" v-model="filterYear">
            <template #default="{ open }">
              <Button 
                :label="filterYear || 'All Years'"
                class="w-full justify-between"
              >
                <template #suffix>
                  <FeatherIcon
                    :name="open ? 'chevron-up' : 'chevron-down'"
                    class="h-4 text-gray-600"
                  />
                </template>
              </Button>
            </template>
          </Dropdown>
        </div>

        <!-- Term Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Term</label>
          <Dropdown :options="termFilterOptions" v-model="filterTerm">
            <template #default="{ open }">
              <Button 
                :label="filterTerm || 'All Terms'"
                class="w-full justify-between"
              >
                <template #suffix>
                  <FeatherIcon
                    :name="open ? 'chevron-up' : 'chevron-down'"
                    class="h-4 text-gray-600"
                  />
                </template>
              </Button>
            </template>
          </Dropdown>
        </div>

       

        <!-- Clear Filters -->
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

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p class="text-gray-600">Loading your reports...</p>
    </div>

    <!-- Reports Grid - 3 Cards Per Row -->
    <div v-else-if="filteredReports.length > 0" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div 
        v-for="report in filteredReports" 
        :key="report.name"
        class="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow"
      >
        <!-- Card Header -->
        <div class="mb-4">
          <h3 class="text-lg font-semibold text-gray-900 mb-1">
            {{ report.academic_year }} - {{ report.assessment_group }} - {{ report.program }}
          </h3>
          <p class="text-sm text-gray-600">{{ report.academic_term }}</p>
        </div>

        <!-- Progress Section -->
        <div v-if="report.total_marks_obtained" class="mb-4">
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm font-medium text-gray-700">Total Score</span>
            <span class="text-sm font-semibold text-gray-900">
              {{ report.total_marks_obtained }}/{{ report.total_max_marks }}
            </span>
          </div>
          
          <!-- Progress Bar -->
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div 
              class="h-2 rounded-full transition-all duration-500"
              :class="getProgressBarColor(report.total_marks_obtained, report.total_max_marks)"
              :style="{ width: `${(report.total_marks_obtained / report.total_max_marks) * 100}%` }"
            ></div>
          </div>
          
          <div class="text-right mt-1">
            <span class="text-xs text-gray-500">
              {{ Math.round((report.total_marks_obtained / report.total_max_marks) * 100) }}%
            </span>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-2 mb-4">
          <div v-if="report.term_average" class="text-center p-3 bg-gray-50 rounded-lg">
            <div class="text-lg font-semibold text-gray-900">{{ report.term_average }}%</div>
            <div class="text-xs text-gray-600">Average</div>
          </div>
          
          <div v-if="report.overall_grade" class="text-center p-3 bg-gray-50 rounded-lg">
            <div class="text-lg font-semibold text-gray-900">{{ report.overall_grade }}</div>
            <div class="text-xs text-gray-600">Grade</div>
          </div>

           <div v-if="report.class_arm_position" class="text-center p-3 bg-gray-50 rounded-lg">
            <div class="text-sm font-semibold text-gray-900">{{ ordinal(report.class_arm_position) }}</div>
            <div class="text-xs text-gray-600">Position</div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex space-x-2 pt-4 border-t">
          <Button
            @click="printReport(report)"
            :loading="printingReports[report.name]"
            size="sm"
            class="flex-1"
          >
            <template #prefix>
              <FeatherIcon name="printer" class="h-4 w-4" />
            </template>
            Print
          </Button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!isLoading" class="text-center py-12">
      <div class="bg-white rounded-lg p-8 shadow-sm border">
        <FeatherIcon name="file-text" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No Reports Found</h3>
        <p class="text-gray-600 mb-4">
          {{ hasFilters ? 'No reports match your current filters.' : 'You don\'t have any reports yet.' }}
        </p>
        <Button v-if="hasFilters" @click="clearFilters" variant="outline">
          Clear Filters
        </Button>
      </div>
    </div>

    <!-- Alert Messages -->
    <div 
      v-if="alertMessage" 
      class="fixed bottom-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-md bg-white border"
      :class="alertType === 'success' ? 'border-green-200' : 'border-red-200'"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center">
          <FeatherIcon 
            :name="alertType === 'success' ? 'check-circle' : 'alert-circle'" 
            class="h-5 w-5 mr-2"
            :class="alertType === 'success' ? 'text-green-600' : 'text-red-600'"
          />
          <span class="text-gray-900">{{ alertMessage }}</span>
        </div>
        <button @click="alertMessage = ''" class="ml-4 text-gray-400 hover:text-gray-600">
          <FeatherIcon name="x" class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { Button, Dropdown, FeatherIcon } from 'frappe-ui'

// Reactive data
const isLoading = ref(false)
const isRefreshing = ref(false)
const alertMessage = ref('')
const alertType = ref('success')
const allReports = ref([])

// Filter states
const filterYear = ref('')
const filterTerm = ref('')
const filterProgram = ref('')

// Track loading states for individual reports
const printingReports = reactive({})

// Progress bar color logic
const getProgressBarColor = (obtained, total) => {
  const percentage = (obtained / total) * 100
  if (percentage >= 75) return 'bg-green-500'
  if (percentage >= 50) return 'bg-yellow-500'
  return 'bg-red-500'
}

// Computed filter options
const academicYearFilterOptions = computed(() => {
  const years = [...new Set(allReports.value.map(r => r.academic_year))].sort()
  return [
    { label: 'All Years', value: '', onClick: () => filterYear.value = '' },
    ...years.map(year => ({
      label: year,
      value: year,
      onClick: () => filterYear.value = year
    }))
  ]
})

const termFilterOptions = computed(() => {
  const terms = [...new Set(allReports.value.map(r => r.assessment_group))].sort()
  return [
    { label: 'All Terms', value: '', onClick: () => filterTerm.value = '' },
    ...terms.map(term => ({
      label: term,
      value: term,
      onClick: () => filterTerm.value = term
    }))
  ]
})

const programFilterOptions = computed(() => {
  const programs = [...new Set(allReports.value.map(r => r.program).filter(Boolean))].sort()
  return [
    { label: 'All Programs', value: '', onClick: () => filterProgram.value = '' },
    ...programs.map(program => ({
      label: program,
      value: program,
      onClick: () => filterProgram.value = program
    }))
  ]
})

// Computed filtered reports
const filteredReports = computed(() => {
  let filtered = [...allReports.value]
  
  if (filterYear.value) {
    filtered = filtered.filter(r => r.academic_year === filterYear.value)
  }
  
  if (filterTerm.value) {
    filtered = filtered.filter(r => r.assessment_group === filterTerm.value)
  }

  if (filterProgram.value) {
    filtered = filtered.filter(r => r.program === filterProgram.value)
  }
  
  // Sort by academic year (desc) then by term
  return filtered.sort((a, b) => {
    if (a.academic_year !== b.academic_year) {
      return b.academic_year.localeCompare(a.academic_year)
    }
    return a.assessment_group.localeCompare(b.assessment_group)
  })
})

const ordinal = (n) => {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

const hasFilters = computed(() => {
  return filterYear.value || filterTerm.value || filterProgram.value
})

// ============================================================================
// API HELPER FUNCTIONS
// ============================================================================

const apiCall = async (endpoint, method = 'GET', data = null) => {
  try {
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    }
    
    if (window.csrf_token) {
      config.headers['X-Frappe-CSRF-Token'] = window.csrf_token
    } else if (window.frappe && window.frappe.csrf_token) {
      config.headers['X-Frappe-CSRF-Token'] = window.frappe.csrf_token
    }
    
    if (data && method !== 'GET') {
      config.body = JSON.stringify(data)
    }
    
    const response = await fetch(endpoint, config)
    const responseText = await response.text()
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${responseText}`)
    }
    
    let result
    try {
      result = JSON.parse(responseText)
    } catch (parseError) {
      throw new Error(`Invalid JSON response: ${responseText}`)
    }
    
    if (result.exc_type || result.exception) {
      throw new Error(result.exception || result.exc_type || 'Server error')
    }
    
    return result
  } catch (error) {
    throw error
  }
}

// ============================================================================
// PRINT FORMAT DETECTION FUNCTIONS
// ============================================================================

/**
 * Check if a program is a secondary/high school program
 * Returns true if program contains keywords indicating secondary education
 */
const isSecondaryProgram = (program) => {
  if (!program) return false
  
  const programLower = program.toLowerCase()
  const secondaryKeywords = [
    'jss',           // Junior Secondary School
    'ss',            // Senior Secondary
    'secondary',
    'high school',
    'senior',
    'junior secondary'
  ]
  
  return secondaryKeywords.some(keyword => programLower.includes(keyword))
}

/**
 * Get the appropriate print format based on the program type
 * Fetches school settings and returns primary or secondary format
 */
const getPrintFormatForProgram = async (program) => {
  try {
    // First get the school settings with both primary and secondary formats
    const result = await apiCall(`/api/method/piamtech_frappe_education.school_portal_api.get_school_print_format`)
    
    const primaryFormat = result.message?.primary_print_format || "Standard"
    const secondaryFormat = result.message?.secondary_print_format || "Standard"
    
    // Check if program is secondary
    const isSecondary = isSecondaryProgram(program)
    
    console.log('Program:', program)
    console.log('Is Secondary:', isSecondary)
    console.log('Primary Format:', primaryFormat)
    console.log('Secondary Format:', secondaryFormat)
    
    // Return the appropriate format
    return isSecondary ? secondaryFormat : primaryFormat
    
  } catch (error) {
    console.error('Error fetching school print format:', error)
    return 'Standard'
  }
}

// ============================================================================
// PDF LINK GENERATION
// ============================================================================


const getPdfLink = (doctype, docname, printFormat = "Standard", noLetterhead = 0) => {
  // Remove pdf_generator parameter entirely - use Frappe's default (wkhtmltopdf)
  return `/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(docname)}&format=${encodeURIComponent(printFormat)}&no_letterhead=${noLetterhead}`;
}


// ============================================================================
// REPORT LOADING AND MANAGEMENT
// ============================================================================

/**
 * Load reports from the server for the current student
 */
const loadReports = async () => {
  try {
    isLoading.value = !allReports.value.length
    isRefreshing.value = true
    
    const result = await apiCall('/api/method/piamtech_frappe_education.school_portal_api.get_student_reports_with_program')
    allReports.value = result.message || []
    
  } catch (error) {
    showAlert('Error loading reports: ' + error.message, 'error')
    allReports.value = []
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

/**
 * Clear all active filters
 */
const clearFilters = () => {
  filterYear.value = ''
  filterTerm.value = ''
  filterProgram.value = ''
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Display an alert message to the user
 */
const showAlert = (message, type = 'success') => {
  alertMessage.value = message
  alertType.value = type
  setTimeout(() => {
    alertMessage.value = ''
  }, 5000)
}

// ============================================================================
// PRINT REPORT FUNCTION
// ============================================================================

/**
 * Handle print report action
 * Gets the appropriate print format based on program type
 * Opens the PDF in a new tab
 */
// const printReport = async (report) => {
//   try {
//     printingReports[report.name] = true

//     // Get the appropriate print format based on the report's program
//     const format = await getPrintFormatForProgram(report.program)
    
//     console.log('===== PRINT REPORT DEBUG =====')
//     console.log('Report Name:', report.name)
//     console.log('Program:', report.program)
//     console.log('Selected Format:', format)
//     console.log('==============================')

//     // Generate the PDF link
//     const pdfUrl = getPdfLink('School Term Result', report.name, format, 1)

//     console.log('Opening PDF URL:', pdfUrl)

//     // Open PDF in a new tab
//     window.open(pdfUrl, '_blank')
//     showAlert('Opening PDF report...', 'success')

//   } catch (error) {
//     console.error('Error printing report:', error)
//     showAlert('Error opening print view: ' + error.message, 'error')
//   } finally {
//     printingReports[report.name] = false
//   }
// }


const printReport = async (report) => {
  try {
    printingReports[report.name] = true

    const format = await getPrintFormatForProgram(report.program)
    
    // Open print preview instead of PDF download
    const printUrl = `/printview?doctype=School%20Term%20Result&name=${encodeURIComponent(report.name)}&format=${encodeURIComponent(format)}&no_letterhead=1`
    
    window.open(printUrl, '_blank')
    showAlert('Opening print preview...', 'success')

  } catch (error) {
    console.error('Error printing report:', error)
    showAlert('Error opening print view: ' + error.message, 'error')
  } finally {
    printingReports[report.name] = false
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.transition-shadow {
  transition: box-shadow 0.2s ease-in-out;
}
</style>