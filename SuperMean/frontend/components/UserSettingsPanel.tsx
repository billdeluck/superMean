// frontend/components/UserSettingsPanel.tsx 
import React, { useState, useEffect, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  UserIcon, CogIcon, LogoutIcon, SunIcon, MoonIcon, BellIcon,
  BellSlashIcon, ClockIcon, LanguageIcon, SaveIcon
} from '@heroicons/react/outline';
import { useRouter } from 'next/router';

interface UserSettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const UserSettingsPanel: React.FC<UserSettingsPanelProps> = ({ isOpen, onClose }) => {
  const router = useRouter();
  const [settings, setSettings] = useState({
    theme: 'light',
    notifications_enabled: true,
    session_timeout_minutes: 60,
    auto_save: true,
    agent_view_mode: 'card',
    language: 'en'
  });
  const [isSaving, setIsSaving] = useState(false);

  // Fetch user settings from API when panel opens
  useEffect(() => {
    if (isOpen) {
      fetchUserSettings();
    }
  }, [isOpen]);

  const fetchUserSettings = async () => {
    try {
      // TODO: Replace with actual API call to fetch user settings
      // const response = await fetch('/api/settings', {
      //   headers: {
      //     'Authorization': `Bearer ${localStorage.getItem('token')}`
      //   }
      // });
      // if (response.ok) {
      //   const data = await response.json();
      //   setSettings(data);
      // } else {
      //   console.error('Failed to fetch settings');
      // }
      // Mock data for now
      setSettings({
        theme: localStorage.getItem('theme') || 'light',
        notifications_enabled: true, // Mock
        session_timeout_minutes: 60, // Mock
        auto_save: true, // Mock
        agent_view_mode: 'card', // Mock
        language: 'en' // Mock
      });
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const saveSettings = async () => {
    setIsSaving(true);
    try {
      // TODO: Replace with actual API call to update user settings
      // const response = await fetch('/api/settings', {
      //   method: 'PUT',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${localStorage.getItem('token')}`
      //   },
      //   body: JSON.stringify(settings)
      // });
      // if (response.ok) {
      //   // Apply theme changes immediately
      //   document.documentElement.classList.toggle('dark', settings.theme === 'dark');
      //   localStorage.setItem('theme', settings.theme);
      //   onClose();
      // } else {
      //   console.error('Failed to save settings');
      // }
      // Mock save
      document.documentElement.classList.toggle('dark', settings.theme === 'dark');
      localStorage.setItem('theme', settings.theme);
      onClose();
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    try {
      // TODO: Replace with actual API call for logout
      // await fetch('/api/logout', {
      //   method: 'POST',
      //   headers: {
      //     'Authorization': `Bearer ${localStorage.getItem('token')}`
      //   }
      // });
      // Clear local storage and cookies
      localStorage.removeItem('token');
      localStorage.removeItem('theme'); // Clear theme as well

      // Redirect to login page or home
      router.push('/');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="fixed inset-0 z-50 overflow-y-auto"
        onClose={onClose}
      >
        <div className="min-h-screen px-4 text-center">
          <Dialog.Overlay className="fixed inset-0 bg-black opacity-30" />

          {/* This element is to trick the browser into centering the modal contents. */}
          <span className="inline-block h-screen align-middle" aria-hidden="true">
            &#8203;
          </span>

          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <div className="inline-block w-full max-w-md p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white dark:bg-gray-800 shadow-xl rounded-2xl">
              <Dialog.Title
                as="h3"
                className="text-lg font-medium leading-6 text-gray-900 dark:text-white flex items-center"
              >
                <UserIcon className="w-5 h-5 mr-2" />
                User Settings
              </Dialog.Title>

              <div className="mt-4 space-y-6">
                {/* Theme Setting */}
                <div>
                  <label className="flex items-center justify-between">
                    <div className="flex items-center">
                      {settings.theme === 'light' ? <SunIcon className="w-5 h-5 mr-2 text-yellow-500" /> :
                       settings.theme === 'dark' ? <MoonIcon className="w-5 h-5 mr-2 text-blue-500" /> :
                       <CogIcon className="w-5 h-5 mr-2 text-gray-500" />
                      }
                      <span>Theme</span>
                    </div>
                    <select
                      value={settings.theme}
                      onChange={(e) => setSettings({...settings, theme: e.target.value})}
                      className="ml-2 p-2 border rounded dark:bg-gray-700 dark:text-white"
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="system">System</option>
                    </select>
                  </label>
                </div>

                {/* Notifications Setting */}
                <div>
                  <label className="flex items-center justify-between">
                    <div className="flex items-center">
                      {settings.notifications_enabled ? <BellIcon className="w-5 h-5 mr-2 text-green-500" /> :
                       <BellSlashIcon className="w-5 h-5 mr-2 text-red-500" />
                      }
                      <span>Notifications</span>
                    </div>
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={settings.notifications_enabled}
                        onChange={(e) => setSettings({...settings, notifications_enabled: e.target.checked})}
                        className="form-checkbox h-5 w-5 text-blue-600"
                      />
                    </label>
                  </label>
                </div>

                {/* Session Timeout Setting */}
                <div>
                  <label className="flex items-center justify-between">
                    <div className="flex items-center">
                      <ClockIcon className="w-5 h-5 mr-2 text-purple-500" />
                      <span>Session Timeout (minutes)</span>
                    </div>
                    <input
                      type="number"
                      min="5"
                      max="240"
                      value={settings.session_timeout_minutes}
                      onChange={(e) => setSettings({...settings, session_timeout_minutes: parseInt(e.target.value, 10)})}
                      className="ml-2 p-2 border rounded w-16 dark:bg-gray-700 dark:text-white"
                    />
                  </label>
                </div>

                {/* Auto Save Setting */}
                <div>
                  <label className="flex items-center justify-between">
                    <div className="flex items-center">
                      <SaveIcon className="w-5 h-5 mr-2 text-indigo-500" />
                      <span>Auto Save</span>
                    </div>
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={settings.auto_save}
                        onChange={(e) => setSettings({...settings, auto_save: e.target.checked})}
                        className="form-checkbox h-5 w-5 text-blue-600"
                      />
                    </label>
                  </label>
                </div>

                {/* Language Setting */}
                <div>
                  <label className="flex items-center justify-between">
                    <div className="flex items-center">
                      <LanguageIcon className="w-5 h-5 mr-2 text-teal-500" />
                      <span>Language</span>
                    </div>
                    <select
                      value={settings.language}
                      onChange={(e) => setSettings({...settings, language: e.target.value})}
                      className="ml-2 p-2 border rounded dark:bg-gray-700 dark:text-white"
                    >
                      <option value="en">English</option>
                      <option value="es">Español</option>
                      <option value="fr">Français</option>
                      <option value="de">Deutsch</option>
                      <option value="zh">中文</option>
                      {/* Add more languages as needed */}
                    </select>
                  </label>
                </div>
              </div>

              <div className="mt-6 flex justify-between items-center">
                <button
                  type="button"
                  className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-red-500"
                  onClick={handleLogout}
                >
                  <LogoutIcon className="w-5 h-5 mr-2" />
                  Logout
                </button>

                <div className="flex space-x-2">
                  <button
                    type="button"
                    className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-transparent rounded-md hover:bg-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-500"
                    onClick={onClose}
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500"
                    onClick={saveSettings}
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : 'Save Settings'}
                  </button>
                </div>
              </div>
            </div>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
};

export default UserSettingsPanel;