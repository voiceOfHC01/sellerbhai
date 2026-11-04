import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Order } from '../types';
import { 
  ShoppingBag, Search, Filter, Download, Edit3, CheckCircle2, 
  Truck, Clock, XCircle, RefreshCw, X, Check, MapPin, Phone, CreditCard 
} from 'lucide-react';

export const OrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Edit form state
  const [editStatus, setEditStatus] = useState<string>('');
  const [editAddress, setEditAddress] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');
  const [editPaymentMethod, setEditPaymentMethod] = useState<string>('');
  const [editDeliveryFee, setEditDeliveryFee] = useState<number>(0);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const params: { status?: string; search?: string } = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const data = await apiClient.orders.getOrders(params);
      setOrders(data);
    } catch (err) {
      console.error('Failed to fetch orders:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchOrders();
  };

  const openEditModal = (order: Order) => {
    setSelectedOrder(order);
    setEditStatus(order.status);
    setEditAddress(order.delivery_address || '');
    setEditNotes(order.notes || '');
    setEditPaymentMethod(order.payment_method || 'COD');
    setEditDeliveryFee(order.delivery_fee || 0);
    setIsEditing(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setSaving(true);
    try {
      const updated = await apiClient.orders.updateOrder(selectedOrder.id, {
        status: editStatus,
        delivery_address: editAddress,
        notes: editNotes,
        payment_method: editPaymentMethod,
        delivery_fee: Number(editDeliveryFee),
      });
      setOrders(orders.map((o) => (o.id === updated.id ? updated : o)));
      setIsEditing(false);
      setSelectedOrder(null);
    } catch (err) {
      alert('Failed to update order.');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleExportCsv = () => {
    const token = localStorage.getItem('replybd_token');
    // Trigger download with auth token header using fetch or window
    fetch('/api/orders/export/csv', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `orders_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch((err) => {
        console.error('CSV export failed:', err);
        alert('Failed to export CSV.');
      });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200 inline-flex items-center gap-1">
            <Clock className="w-3 h-3" /> Pending
          </span>
        );
      case 'confirmed':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Confirmed
          </span>
        );
      case 'shipped':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200 inline-flex items-center gap-1">
            <Truck className="w-3 h-3" /> Shipped
          </span>
        );
      case 'delivered':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 inline-flex items-center gap-1">
            <Check className="w-3 h-3" /> Delivered
          </span>
        );
      case 'cancelled':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200 inline-flex items-center gap-1">
            <XCircle className="w-3 h-3" /> Cancelled
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const statusCounts = {
    all: orders.length,
    pending: orders.filter((o) => o.status === 'pending').length,
    confirmed: orders.filter((o) => o.status === 'confirmed').length,
    shipped: orders.filter((o) => o.status === 'shipped').length,
    delivered: orders.filter((o) => o.status === 'delivered').length,
    cancelled: orders.filter((o) => o.status === 'cancelled').length,
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Orders Dashboard</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              Phase 3 Commerce
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Track automated AI draft orders, update fulfillment statuses, and export CSV reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchOrders}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold shadow-sm transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Status Counters Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        {[
          { id: 'all', label: 'All Orders', count: statusCounts.all, color: 'border-slate-300 bg-white' },
          { id: 'pending', label: 'Pending', count: statusCounts.pending, color: 'border-amber-200 bg-amber-50/50' },
          { id: 'confirmed', label: 'Confirmed', count: statusCounts.confirmed, color: 'border-blue-200 bg-blue-50/50' },
          { id: 'shipped', label: 'Shipped', count: statusCounts.shipped, color: 'border-purple-200 bg-purple-50/50' },
          { id: 'delivered', label: 'Delivered', count: statusCounts.delivered, color: 'border-emerald-200 bg-emerald-50/50' },
          { id: 'cancelled', label: 'Cancelled', count: statusCounts.cancelled, color: 'border-rose-200 bg-rose-50/50' },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setStatusFilter(item.id)}
            className={`p-3.5 rounded-xl border text-left transition-all ${item.color} ${
              statusFilter === item.id ? 'ring-2 ring-blue-600 shadow-sm' : 'hover:border-slate-400'
            }`}
          >
            <span className="text-xs text-slate-500 font-medium block">{item.label}</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">{item.count}</span>
          </button>
        ))}
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <form onSubmit={handleSearch} className="flex-1 flex items-center gap-2 w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by customer name, BD phone (01...), address or order ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-sm font-semibold transition-colors shrink-0"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto text-xs no-scrollbar">
          <span className="text-slate-400 flex items-center gap-1 font-medium">
            <Filter className="w-3.5 h-3.5" /> Filter:
          </span>
          {['all', 'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg capitalize font-medium transition-colors ${
                statusFilter === st
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="p-16 text-center">
            <ShoppingBag className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-900">No orders found</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
              No orders matched your filter. Once customers confirm an order via the AI chat flow, they will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4 text-left">Order #</th>
                  <th className="py-3.5 px-4 text-left">Customer</th>
                  <th className="py-3.5 px-4 text-left">Items</th>
                  <th className="py-3.5 px-4 text-left">Payment</th>
                  <th className="py-3.5 px-4 text-left">Address</th>
                  <th className="py-3.5 px-4 text-left">Total</th>
                  <th className="py-3.5 px-4 text-left">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {orders.map((o) => (
                  <tr key={o.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-4 font-mono font-bold text-slate-900">
                      #{o.id}
                    </td>
                    <td className="py-4 px-4">
                      <div className="font-semibold text-slate-900">{o.customer_name}</div>
                      <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5 font-mono">
                        <Phone className="w-3 h-3 text-slate-400" />
                        {o.customer_phone || 'No phone'}
                      </div>
                    </td>
                    <td className="py-4 px-4 max-w-xs">
                      {o.items.length === 0 ? (
                        <span className="text-slate-400 text-xs">No item details</span>
                      ) : (
                        <div className="space-y-1">
                          {o.items.map((i) => (
                            <div key={i.id} className="text-xs text-slate-700">
                              <span className="font-medium text-slate-900">{i.product_title || 'Item'}</span>
                              {i.variant_sku && (
                                <span className="ml-1 text-[11px] font-mono text-slate-500">
                                  ({i.variant_sku})
                                </span>
                              )}
                              <span className="ml-1 text-slate-500">×{i.quantity}</span>
                              <span className="ml-1.5 font-semibold text-slate-800">৳{i.line_total}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-xs font-semibold uppercase bg-slate-100 text-slate-700 border border-slate-200">
                        {o.payment_method || 'COD'}
                      </span>
                    </td>
                    <td className="py-4 px-4 max-w-xs">
                      <div className="text-xs text-slate-700 line-clamp-2 font-bangla">
                        {o.delivery_address || <span className="text-slate-400 italic">Not provided</span>}
                      </div>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <div className="font-bold text-slate-900">৳{o.total_amount}</div>
                      <div className="text-[11px] text-slate-400">Fee: ৳{o.delivery_fee}</div>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      {getStatusBadge(o.status)}
                    </td>
                    <td className="py-4 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => openEditModal(o)}
                        className="p-1.5 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Edit Order"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit Order Modal */}
      {isEditing && selectedOrder && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Edit Order #{selectedOrder.id}</h3>
                <p className="text-xs text-slate-500">Customer: {selectedOrder.customer_name} ({selectedOrder.customer_phone})</p>
              </div>
              <button
                onClick={() => setIsEditing(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Order Status
                </label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-semibold focus:ring-2 focus:ring-blue-600 focus:outline-none"
                >
                  <option value="pending">Pending</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="shipped">Shipped</option>
                  <option value="delivered">Delivered</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Payment Method
                </label>
                <select
                  value={editPaymentMethod}
                  onChange={(e) => setEditPaymentMethod(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-semibold focus:ring-2 focus:ring-blue-600 focus:outline-none"
                >
                  <option value="COD">COD (Cash on Delivery)</option>
                  <option value="bKash">bKash</option>
                  <option value="Nagad">Nagad</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Delivery Address
                </label>
                <textarea
                  rows={2}
                  value={editAddress}
                  onChange={(e) => setEditAddress(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-600 focus:outline-none font-bangla"
                  placeholder="Full delivery address..."
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                    Delivery Fee (৳)
                  </label>
                  <input
                    type="number"
                    value={editDeliveryFee}
                    onChange={(e) => setEditDeliveryFee(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                    Internal Notes
                  </label>
                  <input
                    type="text"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-600 focus:outline-none"
                    placeholder="e.g. Call before delivery"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
