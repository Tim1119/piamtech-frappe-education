<template>
  <div>
    <Dialog
      :options="{
        title: 'Pay Invoice',
        actions: [{ label: 'Proceed', variant: 'solid' }],
      }"
      :modelValue="modelValue"
      @update:modelValue="emits('update:modelValue', $event)"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <!-- Complete Fee Breakdown Card -->
          <div class="bg-gray-50 border rounded-lg p-4">
            <h3 class="text-sm font-semibold text-gray-900 mb-4">Complete Fee Breakdown</h3>
            <div class="space-y-3 text-sm">
              <div class="flex justify-between items-center">
                <span class="text-gray-600">Original Invoice Amount:</span>
                <span class="font-semibold text-gray-900 text-base">{{ getOriginalAmount() }}</span>
              </div>
              
              <div class="border-t pt-3">
                <p class="text-gray-600 mb-2 font-medium">Payments Made:</p>
                <div class="pl-4 space-y-1">
                  <div class="flex justify-between">
                    <span class="text-gray-600">Total Paid:</span>
                    <span class="font-semibold text-green-600">{{ getAmountPaid() }}</span>
                  </div>
                </div>
              </div>

              <div class="border-t pt-3 bg-red-50 p-3 rounded">
                <div class="flex justify-between">
                  <span class="text-gray-700 font-medium">Outstanding Balance:</span>
                  <span class="font-semibold text-red-600 text-base">{{ getOutstanding() }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Invoice Details -->
          <div class="border-t pt-4">
            <h3 class="text-sm font-semibold text-gray-900 mb-3">Invoice Details</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">Student:</span>
                <span class="font-semibold">{{ student.student_name }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Student ID:</span>
                <span class="font-semibold">{{ student.name }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Program:</span>
                <span class="font-semibold">{{ row.program }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Invoice:</span>
                <span class="font-semibold text-blue-600">{{ row.invoice }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Status:</span>
                <Badge
                  variant="subtle"
                  :theme="badgeColor(row.status)"
                  size="sm"
                  :label="row.status"
                />
              </div>
            </div>
          </div>

          <!-- Payment Type Selection -->
          <div class="border-t pt-4">
            <h3 class="text-sm font-semibold text-gray-900 mb-3">Payment Type</h3>
            <div class="grid grid-cols-2 gap-3">
              <button
                @click="paymentType = 'Full'"
                :class="[
                  'p-3 rounded-lg border-2 transition-colors text-sm font-medium',
                  paymentType === 'Full'
                    ? 'border-blue-600 bg-blue-50 text-blue-900'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                ]"
              >
                Full Payment
              </button>
              <button
                @click="paymentType = 'Partial'"
                :class="[
                  'p-3 rounded-lg border-2 transition-colors text-sm font-medium',
                  paymentType === 'Partial'
                    ? 'border-blue-600 bg-blue-50 text-blue-900'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                ]"
              >
                Partial Payment
              </button>
            </div>
          </div>

          <!-- Payment Amount Section - Only show for Partial -->
          <div v-if="paymentType === 'Partial'" class="border-t pt-4">
            <h3 class="text-sm font-semibold text-gray-900 mb-4">Amount to Pay</h3>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Enter Amount *
              </label>
              <div class="relative">
                <span class="absolute left-3 top-3 text-gray-600">₦</span>
                <FormControl
                  type="number"
                  v-model.number="paymentAmount"
                  placeholder="0.00"
                  class="pl-8"
                  step="0.01"
                  @change="validatePaymentAmount"
                />
              </div>
              <ErrorMessage
                v-if="paymentError"
                :message="paymentError"
                class="pt-2"
              />

              <!-- Payment breakdown for partial -->
              <div class="mt-3 p-3 bg-gray-50 rounded text-sm space-y-2">
                <div class="flex justify-between">
                  <span class="text-gray-600">Outstanding Balance:</span>
                  <span class="font-semibold text-gray-900">{{ getOutstanding() }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">You are paying:</span>
                  <span class="font-semibold text-gray-900">
                    {{ paymentAmount ? formatCurrency(paymentAmount) : '₦0.00' }}
                  </span>
                </div>
                <div v-if="paymentAmount" class="flex justify-between border-t pt-2">
                  <span class="text-gray-600">Balance after payment:</span>
                  <span class="font-semibold text-gray-900">
                    {{ getRemainingAfter() }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Full Payment Summary -->
          <div v-else class="border-t pt-4 bg-gray-50 p-3 rounded">
            <p class="text-sm text-gray-600 mb-2">You will pay the full outstanding:</p>
            <p class="font-semibold text-lg text-gray-900">{{ getOutstanding() }}</p>
          </div>

          <!-- Contact Information -->
          <div class="border-t pt-4">
            <h3 class="text-sm font-semibold text-gray-900 mb-4">Contact Information</h3>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Email Address *</label>
                <FormControl
                  type="email"
                  v-model="billingDetails.email"
                  placeholder="your@email.com"
                />
                <ErrorMessage
                  v-if="!billingDetails.email"
                  message="Email is required"
                  class="pt-2"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Phone Number *</label>
                <FormControl
                  type="tel"
                  v-model="billingDetails.mobile_number"
                  placeholder="+234 800 000 0000"
                />
                <ErrorMessage
                  v-if="!billingDetails.mobile_number"
                  message="Phone number is required"
                  class="pt-2"
                />
              </div>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="isProcessing" class="flex items-center justify-center py-4">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span class="ml-2 text-gray-600">Processing payment...</span>
          </div>

          <!-- Info Message -->
          <div class="bg-green-50 border border-green-200 rounded p-3">
            <p class="text-sm text-green-800">
              ✓ You will be securely redirected to Paystack to complete your payment.
            </p>
          </div>
        </div>
      </template>

      <template #actions="{ close }">
        <div class="flex flex-row-reverse gap-2">
          <Button
            class="h-9"
            variant="solid"
            @click="proceedToPayment()"
            icon-left="external-link"
            :loading="isProcessing"
            label="Proceed to Payment"
            :disabled="!isFormValid() || isProcessing"
          />
          <Button
            class="h-9"
            variant="outline"
            @click="close"
            label="Cancel"
            :disabled="isProcessing"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { FormControl, Dialog, Button, Badge, ErrorMessage, call } from 'frappe-ui'
import { createToast } from '../utils'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: false,
  },
  student: {
    type: Object,
    required: true,
  },
  row: {
    type: Object,
    required: true,
  },
})

const emits = defineEmits(['update:modelValue', 'success'])

const isProcessing = ref(false)
const paymentType = ref('Full')
const paymentAmount = ref(null)
const paymentError = ref('')

const billingDetails = reactive({
  email: props.student.student_email_id || props.student.email || '',
  mobile_number: props.student.phone || '',
})

const getOriginalAmount = () => {
  return props.row.original_amount || props.row.amount || '₦0.00'
}

const getAmountPaid = () => {
  return props.row.amount_paid || '₦0.00'
}

const getOutstanding = () => {
  return props.row.amount_outstanding || '₦0.00'
}

const getRemainingAfter = () => {
  const outstanding = parseFloat(props.row.amount_outstanding_raw) || 0
  const paying = paymentAmount.value || 0
  const remaining = outstanding - paying
  return formatCurrency(remaining > 0 ? remaining : 0)
}

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
  }).format(amount)
}

const validatePaymentAmount = () => {
  paymentError.value = ''
  const outstanding = parseFloat(props.row.amount_outstanding_raw) || 0
  
  if (!paymentAmount.value || paymentAmount.value <= 0) {
    paymentError.value = 'Amount must be greater than zero'
    return false
  }
  
  if (paymentAmount.value > outstanding) {
    paymentError.value = `Amount cannot exceed outstanding balance (${formatCurrency(outstanding)})`
    return false
  }
  
  return true
}

const isFormValid = () => {
  if (paymentType.value === 'Full') {
    return billingDetails.email && billingDetails.mobile_number
  }
  
  return (
    billingDetails.email &&
    billingDetails.mobile_number &&
    paymentAmount.value &&
    paymentAmount.value > 0 &&
    validatePaymentAmount()
  )
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

const proceedToPayment = async () => {
  if (!isFormValid()) {
    createToast({
      title: 'Validation Error',
      description: 'Please fill in all required fields correctly',
      icon: 'alert-circle',
      iconClasses: 'text-red-600',
    })
    return
  }

  isProcessing.value = true

  try {
    const outstanding = parseFloat(props.row.amount_outstanding_raw) || 0
    const amountToPay = paymentType.value === 'Full' ? outstanding : paymentAmount.value

    const result = await call('piamtech_frappe_education.paystack.initiate_payment', {
      sales_invoice: props.row.invoice,
      payment_amount: amountToPay,
      email: billingDetails.email
    })

    if (result.success) {
      window.location.href = result.authorization_url
    } else {
      createToast({
        title: 'Payment Error',
        description: result.message || 'Failed to initiate payment',
        icon: 'x',
        iconClasses: 'text-red-600',
      })
      isProcessing.value = false
    }
  } catch (error) {
    console.error('Payment error:', error)
    createToast({
      title: 'Error',
      description: error.message || 'Failed to process payment',
      icon: 'x',
      iconClasses: 'text-red-600',
    })
    isProcessing.value = false
  }
}
</script>