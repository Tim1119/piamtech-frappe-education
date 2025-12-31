<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Page Header -->
    <div class="bg-white border-b px-6 py-4">
      <h1 class="text-2xl font-bold text-gray-900">My Fees</h1>
      <p class="text-gray-600 mt-1">View and pay your school fees</p>
    </div>

    <!-- Main Content -->
    <div class="p-6">
      <!-- Loading State -->
      <div v-if="invoicesResource.loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-600">Loading your fees...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="invoicesResource.error" class="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
        <div class="flex items-start">
          <FeatherIcon name="alert-circle" class="h-5 w-5 text-red-600 mt-0.5 mr-3" />
          <div>
            <h3 class="text-sm font-medium text-red-800">Error Loading Fees</h3>
            <p class="text-sm text-red-700 mt-1">{{ invoicesResource.error }}</p>
            <Button
              @click="invoicesResource.reload()"
              variant="outline"
              size="sm"
              class="mt-3"
              label="Try Again"
            />
          </div>
        </div>
      </div>

      <!-- Fees Table -->
      <div v-else-if="tableData.rows.length > 0" class="bg-white rounded-lg border shadow-sm overflow-hidden">
        <ListView
          :columns="tableData.columns"
          :rows="tableData.rows"
          :options="{
            selectable: false,
            showTooltip: false,
            onRowClick: () => {},
          }"
          row-key="invoice"
        >
          <ListHeader>
            <ListHeaderItem
              v-for="column in tableData.columns"
              :key="column.key"
              :item="column"
            />
          </ListHeader>
          <ListRow
            v-for="row in tableData.rows"
            :key="row.invoice"
            :row="row"
            v-slot="{ column, item }"
          >
            <ListRowItem :item="item" :align="column.align">
              <!-- Status Badge -->
              <Badge
                v-if="column.key === 'status'"
                variant="subtle"
                :theme="badgeColor(row.status)"
                size="md"
                :label="item"
              />

              <!-- Program -->
              <span v-else-if="column.key === 'program'" class="text-gray-900 font-medium">
                {{ item }}
              </span>

              <!-- Original Amount -->
              <span v-else-if="column.key === 'original_amount'" class="font-semibold text-gray-900">
                {{ item }}
              </span>

              <!-- Amount Paid -->
              <span v-else-if="column.key === 'amount_paid'" class="text-green-600 font-semibold">
                {{ item }}
              </span>

              <!-- Outstanding -->
              <span v-else-if="column.key === 'amount_outstanding'" :class="getOutstandingColor(row.amount_outstanding_raw)">
                {{ item }}
              </span>

              <!-- Due Date -->
              <span v-else-if="column.key === 'due_date'" class="text-gray-700">
                {{ item === '-' ? 'N/A' : formatDate(item) }}
              </span>

              <!-- Actions -->
              <div v-else-if="column.key === 'cta'" class="flex gap-2">
                <Button
                  v-if="row.status === 'Paid'"
                  @click="downloadInvoice(row)"
                  variant="outline"
                  size="sm"
                  icon-left="download"
                  label="Download"
                />

                <Button
                  v-else
                  @click="openPaymentDialog(row)"
                  variant="solid"
                  size="sm"
                  icon-left="credit-card"
                  label="Pay Now"
                />
              </div>
            </ListRowItem>
          </ListRow>
        </ListView>
      </div>

      <!-- Empty State -->
      <div v-else class="bg-white rounded-lg border p-12 text-center">
        <FeatherIcon name="inbox" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No Fees Found</h3>
        <p class="text-gray-600">You don't have any fees at the moment.</p>
      </div>
    </div>

    <!-- Payment Dialog -->
    <FeesPaymentDialog
      v-if="currentRow"
      :row="currentRow"
      :student="studentInfo"
      v-model="showPaymentDialog"
      @success="onPaymentSuccess()"
    />
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRow,
  ListRowItem,
  Badge,
  Button,
  FeatherIcon,
  createResource,
  call,
} from 'frappe-ui'
import FeesPaymentDialog from '@/components/FeesPaymentDialog.vue'
import { studentStore } from '@/stores/student'
import { createToast } from '@/utils'

const { getStudentInfo } = studentStore()
const studentInfo = ref(getStudentInfo().value)

// Check for payment callback
onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  
  if (params.has('success')) {
    createToast({
      title: 'Payment Successful! 🎉',
      description: 'Your payment has been processed. Fees updated.',
      icon: 'check',
      iconClasses: 'text-green-600',
    })
    // Reload fees
    setTimeout(() => {
      invoicesResource.reload()
      // Clean up URL
      window.history.replaceState({}, document.title, '/app/student-portal/fees')
    }, 1000)
  }
  
  if (params.has('error')) {
    const error = params.get('error')
    const errorMessages = {
      'verification_failed': 'Payment verification failed. Please contact support.',
      'payment_processing_failed': 'Error processing your payment. Please try again.',
      'payment_failed': 'Payment was declined. Please try again.',
      'verification_error': 'An error occurred during verification. Please try again.',
    }
    
    createToast({
      title: 'Payment Error',
      description: errorMessages[error] || 'An error occurred during payment.',
      icon: 'x',
      iconClasses: 'text-red-600',
    })
    // Clean up URL
    window.history.replaceState({}, document.title, '/app/student-portal/fees')
  }
})

// Load student invoices from enhanced API
const invoicesResource = createResource({
  url: 'piamtech_frappe_education.school_portal_api.get_student_invoices_with_details',
  params: {
    student: studentInfo.value.name,
  },
  onSuccess: (response) => {
    let invoices = response?.invoices || []
    
    // Format invoice data with currency
    invoices = invoices.map(invoice => {
      const originalAmount = invoice.original_amount || 0
      const totalPaid = invoice.total_paid || 0
      const outstandingAmount = invoice.outstanding_amount || 0
      
      return {
        ...invoice,
        original_amount: formatCurrency(originalAmount),
        original_amount_raw: originalAmount,
        amount_paid: formatCurrency(totalPaid),
        amount_paid_raw: totalPaid,
        amount_outstanding: formatCurrency(outstandingAmount),
        amount_outstanding_raw: outstandingAmount,
      }
    })
    
    // Sort by status (Overdue > Unpaid > Partly Paid > Paid)
    invoices = invoices.sort((a, b) => {
      const statusOrder = { Overdue: 0, Unpaid: 1, 'Partly Paid': 2, Paid: 3 }
      const statusA = statusOrder[a.status] ?? 99
      const statusB = statusOrder[b.status] ?? 99
      return statusA - statusB
    })
    
    tableData.rows = invoices
    printFormat.value = response?.print_format || 'Standard'
  },
  onError: (err) => {
    createToast({
      title: 'Error loading fees',
      icon: 'x',
      iconClasses: 'text-red-600',
    })
  },
  auto: true,
})

const tableData = reactive({
  rows: [],
  columns: [
    {
      label: 'Program',
      key: 'program',
      width: 1,
    },
    {
      label: 'Status',
      key: 'status',
      width: 1,
    },
    {
      label: 'Original Amount',
      key: 'original_amount',
      width: 1,
    },
    {
      label: 'Amount Paid',
      key: 'amount_paid',
      width: 1,
    },
    {
      label: 'Outstanding',
      key: 'amount_outstanding',
      width: 1,
    },
    {
      label: 'Due Date',
      key: 'due_date',
      width: 1,
    },
    {
      label: 'Action',
      key: 'cta',
      width: 1,
    },
  ],
})

const currentRow = ref(null)
const showPaymentDialog = ref(false)
const printFormat = ref('Standard')

const formatDate = (dateString) => {
  if (!dateString || dateString === '-') return '-'
  return new Date(dateString).toLocaleDateString('en-NG', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
  }).format(amount)
}

const badgeColor = (status) => {
  const badgeColorMap = {
    Paid: 'green',
    Unpaid: 'red',
    Overdue: 'red',
    'Partly Paid': 'orange',
  }
  return badgeColorMap[status]
}

const getOutstandingColor = (amount) => {
  if (amount === 0) {
    return 'text-green-600 font-semibold'
  } else if (amount > 0) {
    return 'text-red-600 font-semibold'
  }
  return 'text-gray-700'
}

const downloadInvoice = (row) => {
  const url = `/api/method/frappe.utils.print_format.download_pdf?` +
    `doctype=${encodeURIComponent('Sales Invoice')}` +
    `&name=${encodeURIComponent(row.invoice)}` +
    `&format=${encodeURIComponent(printFormat.value)}`
  
  window.open(url, '_blank')
}

const openPaymentDialog = (row) => {
  currentRow.value = row
  showPaymentDialog.value = true
}

const onPaymentSuccess = () => {
  invoicesResource.reload()
  createToast({
    title: 'Payment successful!',
    description: 'Your payment has been processed',
    icon: 'check',
    iconClasses: 'text-green-600',
  })
}
</script>