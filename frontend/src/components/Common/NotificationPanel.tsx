'use client'

import React from 'react';
import { Drawer, List, Button, Typography, Badge, Space, Empty } from 'antd';
import { CloseOutlined, CheckOutlined, DeleteOutlined } from '@ant-design/icons';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { markNotificationRead, removeNotification } from '@/store/slices/uiSlice';

const { Title, Text } = Typography;

interface NotificationPanelProps {
  visible: boolean;
  onClose: () => void;
}

const NotificationPanel: React.FC<NotificationPanelProps> = ({ visible, onClose }) => {
  const dispatch = useAppDispatch();
  const notifications = useAppSelector((state) => state.ui.notifications);

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'success':
        return '#52c41a';
      case 'error':
        return '#ff4d4f';
      case 'warning':
        return '#faad14';
      default:
        return '#1890ff';
    }
  };

  const markAllAsRead = () => {
    notifications.forEach(notification => {
      if (!notification.read) {
        dispatch(markNotificationRead(notification.id));
      }
    });
  };

  const clearAll = () => {
    notifications.forEach(notification => {
      dispatch(removeNotification(notification.id));
    });
  };

  return (
    <Drawer
      title={
        <div className="flex items-center justify-between">
          <Title level={4} className="m-0">
            Notifications
          </Title>
          <Space>
            <Button
              type="text"
              size="small"
              icon={<CheckOutlined />}
              onClick={markAllAsRead}
            >
              Mark all read
            </Button>
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              onClick={clearAll}
            >
              Clear all
            </Button>
          </Space>
        </div>
      }
      placement="right"
      onClose={onClose}
      open={visible}
      width={400}
      closeIcon={<CloseOutlined />}
    >
      {notifications.length === 0 ? (
        <Empty
          description="No notifications"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          dataSource={notifications.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())}
          renderItem={(notification) => (
            <List.Item
              className={`p-4 border-b border-gray-100 dark:border-gray-700 ${
                !notification.read ? 'bg-blue-50 dark:bg-blue-900/20' : ''
              }`}
              actions={[
                <Button
                  key="delete"
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => dispatch(removeNotification(notification.id))}
                />,
              ]}
            >
              <div className="flex items-start space-x-3 w-full">
                <Badge
                  color={getNotificationColor(notification.type)}
                  className="mt-1"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <Text strong className="text-sm">
                      {notification.title}
                    </Text>
                    {!notification.read && (
                      <Badge status="processing" />
                    )}
                  </div>
                  <Text className="text-sm text-gray-600 dark:text-gray-400 block mb-2">
                    {notification.message}
                  </Text>
                  <Text className="text-xs text-gray-400">
                    {new Date(notification.timestamp).toLocaleString()}
                  </Text>
                  {!notification.read && (
                    <Button
                      type="link"
                      size="small"
                      className="p-0 h-auto mt-1"
                      onClick={() => dispatch(markNotificationRead(notification.id))}
                    >
                      Mark as read
                    </Button>
                  )}
                </div>
              </div>
            </List.Item>
          )}
        />
      )}
    </Drawer>
  );
};

export default NotificationPanel;