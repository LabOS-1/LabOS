'use client'

import React, { useEffect } from 'react';
import { useAppSelector } from '@/store/hooks';
import DraggableIntercom from './DraggableIntercom';

// Intercom types
declare global {
  interface Window {
    Intercom: any;
    intercomSettings: any;
    attachEvent?: any;
  }
}

// Extended user type
interface ExtendedUser {
  id?: string;
  sub?: string;
  user_id?: string;
  email?: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  created_at?: string;
  status?: string;
  is_admin?: boolean;
  job_title?: string;
  organization?: string;
  country?: string;
  picture?: string;
  email_verified?: boolean;
}

const INTERCOM_APP_ID = process.env.NEXT_PUBLIC_INTERCOM_APP_ID || 'czvfsb37';

export const IntercomProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);

  useEffect(() => {
    // Load Intercom script
    if (typeof window !== 'undefined') {
      (function(){
        var w = window;
        var ic = w.Intercom;
        if (typeof ic === "function") {
          ic('reattach_activator');
          ic('update', w.intercomSettings);
        } else {
          var d = document;
          var i: any = function(){
            i.c(arguments);
          };
          i.q = [];
          i.c = function(args: any){
            i.q.push(args);
          };
          w.Intercom = i;
          var l = function(){
            var s = d.createElement('script');
            s.type = 'text/javascript';
            s.async = true;
            s.src = 'https://widget.intercom.io/widget/' + INTERCOM_APP_ID;
            var x = d.getElementsByTagName('script')[0];
            x.parentNode!.insertBefore(s, x);
          };
          if (document.readyState === 'complete'){
            l();
          } else if (w.attachEvent){
            w.attachEvent('onload', l);
          } else {
            w.addEventListener('load', l, false);
          }
        }
      })();
    }
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.Intercom) {
      if (isAuthenticated && user) {
        // Cast user to ExtendedUser type
        const extendedUser = user as ExtendedUser;

        // Boot Intercom with user data and custom launcher position
        window.Intercom('boot', {
          app_id: INTERCOM_APP_ID,
          user_id: extendedUser.sub || extendedUser.user_id || extendedUser.id,
          name: extendedUser.name || `${extendedUser.first_name || ''} ${extendedUser.last_name || ''}`.trim() || undefined,
          email: extendedUser.email,
          created_at: extendedUser.created_at ? Math.floor(new Date(extendedUser.created_at).getTime() / 1000) : undefined,
          // Custom attributes
          user_status: extendedUser.status,
          is_admin: extendedUser.is_admin,
          job_title: extendedUser.job_title,
          organization: extendedUser.organization,
          country: extendedUser.country,
          // Hide default launcher
          hide_default_launcher: true,
        });
      } else {
        // Boot Intercom for visitors (no user data) with custom position
        window.Intercom('boot', {
          app_id: INTERCOM_APP_ID,
          // Hide default launcher
          hide_default_launcher: true,
        });
      }

      // No need for JavaScript adjustments - using Intercom's official API
    }
  }, [isAuthenticated, user]);

  // Update Intercom when user navigates
  useEffect(() => {
    if (typeof window !== 'undefined' && window.Intercom) {
      window.Intercom('update');
    }
  });

  return (
    <>
      {children}
      <DraggableIntercom />
    </>
  );
};

export default IntercomProvider;

